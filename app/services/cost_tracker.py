"""
成本控制模块
追踪 DeepSeek API 调用成本，支持日/月限额控制
"""
import time
from datetime import datetime, timedelta
from typing import Optional, Dict
from sqlalchemy import Column, String, Integer, Float, DateTime, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import Base, async_session_factory
from app.config import settings
from app.utils.logger import logger


class CostRecord(Base):
    """成本记录表"""
    __tablename__ = "cost_records"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), nullable=True)
    provider = Column(String(50), nullable=False)  # deepseek/minimax
    model = Column(String(50), nullable=False)
    
    # Token 统计
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    
    # 成本（元）
    cost = Column(Float, default=0.0)
    
    # 时间
    created_at = Column(DateTime, default=datetime.utcnow)


class CostTracker:
    """成本追踪器"""
    
    # DeepSeek 定价（元/千token）
    PRICING = {
        "deepseek-v4-flash": {
            "input": 0.001,   # 输入 0.001 元/千token
            "output": 0.002,  # 输出 0.002 元/千token
        },
        "deepseek-v4-pro": {
            "input": 0.002,
            "output": 0.008,
        }
    }
    
    def __init__(self):
        # 从 settings 读取配置，而非硬编码
        self.daily_limit = settings.COST_DAILY_LIMIT
        self.monthly_limit = settings.COST_MONTHLY_LIMIT
        self.warn_threshold = settings.COST_WARN_THRESHOLD
    
    def calculate_cost(
        self, 
        model: str, 
        prompt_tokens: int, 
        completion_tokens: int
    ) -> float:
        """
        计算调用成本
        
        Args:
            model: 模型名称
            prompt_tokens: 输入 token 数
            completion_tokens: 输出 token 数
            
        Returns:
            成本（元）
        """
        pricing = self.PRICING.get(model, self.PRICING["deepseek-v4-flash"])
        
        input_cost = (prompt_tokens / 1000) * pricing["input"]
        output_cost = (completion_tokens / 1000) * pricing["output"]
        
        return round(input_cost + output_cost, 6)
    
    async def record_usage(
        self,
        db: AsyncSession,
        user_id: Optional[str],
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int
    ) -> float:
        """
        记录 API 调用
        
        Returns:
            本次调用成本
        """
        cost = self.calculate_cost(model, prompt_tokens, completion_tokens)
        
        record = CostRecord(
            user_id=user_id,
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost=cost
        )
        db.add(record)
        await db.commit()
        
        logger.info(
            f"[Cost] {provider}/{model}: "
            f"tokens={prompt_tokens+completion_tokens}, "
            f"cost={cost:.4f}元"
        )
        
        return cost
    
    async def get_daily_cost(
        self, 
        db: AsyncSession, 
        provider: str = "deepseek"
    ) -> float:
        """获取今日成本"""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        result = await db.execute(
            select(func.sum(CostRecord.cost))
            .where(CostRecord.provider == provider)
            .where(CostRecord.created_at >= today)
        )
        
        return result.scalar() or 0.0
    
    async def get_monthly_cost(
        self, 
        db: AsyncSession, 
        provider: str = "deepseek"
    ) -> float:
        """获取本月成本"""
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        result = await db.execute(
            select(func.sum(CostRecord.cost))
            .where(CostRecord.provider == provider)
            .where(CostRecord.created_at >= month_start)
        )
        
        return result.scalar() or 0.0
    
    async def check_budget(
        self, 
        db: AsyncSession, 
        provider: str = "deepseek"
    ) -> Dict:
        """
        检查预算状态
        
        Returns:
            {"allowed": bool, "daily_cost": float, "monthly_cost": float, "message": str}
        """
        daily_cost = await self.get_daily_cost(db, provider)
        monthly_cost = await self.get_monthly_cost(db, provider)
        
        # 检查日限额
        if daily_cost >= self.daily_limit:
            return {
                "allowed": False,
                "daily_cost": daily_cost,
                "monthly_cost": monthly_cost,
                "message": f"已达到日限额 {self.daily_limit} 元"
            }
        
        # 检查月限额
        if monthly_cost >= self.monthly_limit:
            return {
                "allowed": False,
                "daily_cost": daily_cost,
                "monthly_cost": monthly_cost,
                "message": f"已达到月限额 {self.monthly_limit} 元"
            }
        
        # 预警检查
        daily_ratio = daily_cost / self.daily_limit
        monthly_ratio = monthly_cost / self.monthly_limit
        
        if daily_ratio >= self.warn_threshold or monthly_ratio >= self.warn_threshold:
            return {
                "allowed": True,
                "daily_cost": daily_cost,
                "monthly_cost": monthly_cost,
                "message": f"预算预警: 日用 {daily_ratio:.0%}, 月用 {monthly_ratio:.0%}"
            }
        
        return {
            "allowed": True,
            "daily_cost": daily_cost,
            "monthly_cost": monthly_cost,
            "message": "正常"
        }
    
    async def get_usage_stats(
        self, 
        db: AsyncSession, 
        days: int = 30
    ) -> Dict:
        """
        获取使用统计
        
        Returns:
            统计信息字典
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # 总调用次数
        result = await db.execute(
            select(func.count(CostRecord.id))
            .where(CostRecord.created_at >= start_date)
        )
        total_calls = result.scalar() or 0
        
        # 总 token 数
        result = await db.execute(
            select(func.sum(CostRecord.total_tokens))
            .where(CostRecord.created_at >= start_date)
        )
        total_tokens = result.scalar() or 0
        
        # 总成本
        result = await db.execute(
            select(func.sum(CostRecord.cost))
            .where(CostRecord.created_at >= start_date)
        )
        total_cost = result.scalar() or 0.0
        
        return {
            "period_days": days,
            "total_calls": total_calls,
            "total_tokens": total_tokens,
            "total_cost": round(total_cost, 4)
        }


# 全局成本追踪器实例
cost_tracker = CostTracker()
