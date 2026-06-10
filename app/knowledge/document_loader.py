"""
文档加载器
支持加载 md/txt/pdf/docx 格式的文档并分块存储
"""
import os
import re
from typing import List, Dict, Optional, Any
from pathlib import Path

from app.utils.logger import logger


class DocumentLoader:
    """
    文档加载器
    
    支持格式：
    - .md: Markdown 文档，按段落分块
    - .txt: 纯文本，按段落分块
    - .pdf: PDF 文档（需要 pdfplumber）
    - .docx: Word 文档（需要 python-docx）
    """
    
    # 支持的文件扩展名
    SUPPORTED_FORMATS = {".md", ".txt", ".pdf", ".docx"}
    
    # 默认分块大小（字符数）
    DEFAULT_CHUNK_SIZE = 800  # 法律文档建议 800-1000
    
    # 分块重叠大小
    DEFAULT_CHUNK_OVERLAP = 100
    
    def __init__(
        self, 
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
    ):
        """
        初始化文档加载器
        
        Args:
            chunk_size: 分块大小（字符数）
            chunk_overlap: 分块重叠大小
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def load_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        加载单个文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            文档块列表
        """
        path = Path(file_path)
        
        if not path.exists():
            logger.error(f"[DocLoader] 文件不存在: {file_path}")
            return []
        
        if path.suffix.lower() not in self.SUPPORTED_FORMATS:
            logger.warning(f"[DocLoader] 不支持的文件格式: {path.suffix}")
            return []
        
        try:
            # 根据文件类型选择加载方法
            if path.suffix.lower() == ".md":
                content = self._load_markdown(file_path)
            elif path.suffix.lower() == ".txt":
                content = self._load_text(file_path)
            elif path.suffix.lower() == ".pdf":
                content = self._load_pdf(file_path)
            elif path.suffix.lower() == ".docx":
                content = self._load_docx(file_path)
            else:
                return []
            
            if not content:
                logger.warning(f"[DocLoader] 文件内容为空: {file_path}")
                return []
            
            # 根据文档类型选择切割策略
            if path.suffix.lower() == ".docx":
                chunks = self._split_legal_document(content)
            else:
                chunks = self._split_text(content)
            
            # 构建文档块
            documents = []
            for i, chunk in enumerate(chunks):
                documents.append({
                    "content": chunk,
                    "metadata": {
                        "source": str(path.name),
                        "file_path": str(path.absolute()),
                        "file_type": path.suffix.lower(),
                        "chunk_index": i,
                        "total_chunks": len(chunks)
                    }
                })
            
            logger.info(f"[DocLoader] 加载文件: {path.name}, 分块数: {len(chunks)}")
            return documents
            
        except Exception as e:
            logger.error(f"[DocLoader] 加载文件失败: {file_path}, 错误: {e}")
            return []
    
    def load_directory(self, dir_path: str) -> List[Dict[str, Any]]:
        """
        加载目录下所有支持的文件
        
        Args:
            dir_path: 目录路径
            
        Returns:
            所有文档块列表
        """
        path = Path(dir_path)
        
        if not path.exists():
            logger.error(f"[DocLoader] 目录不存在: {dir_path}")
            return []
        
        all_documents = []
        
        for file_path in path.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in self.SUPPORTED_FORMATS:
                documents = self.load_file(str(file_path))
                all_documents.extend(documents)
        
        logger.info(f"[DocLoader] 加载目录: {dir_path}, 总分块数: {len(all_documents)}")
        return all_documents
    
    def _load_markdown(self, file_path: str) -> str:
        """加载 Markdown 文件"""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 简单处理：移除 markdown 标记，保留文本
        content = re.sub(r'^#{1,6}\s+', '', content, flags=re.MULTILINE)
        content = re.sub(r'\*\*(.*?)\*\*', r'\1', content)
        content = re.sub(r'\*(.*?)\*', r'\1', content)
        content = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
        content = re.sub(r'`(.*?)`', r'\1', content)
        
        return content
    
    def _load_text(self, file_path: str) -> str:
        """加载纯文本文件"""
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    
    def _load_pdf(self, file_path: str) -> str:
        """加载 PDF 文件"""
        try:
            import pdfplumber
            
            content = ""
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        content += page_text + "\n"
            
            return content
            
        except ImportError:
            logger.error("[DocLoader] pdfplumber 未安装，请运行: pip install pdfplumber")
            return ""
        except Exception as e:
            logger.error(f"[DocLoader] PDF 加载失败: {e}")
            return ""
    
    def _load_docx(self, file_path: str) -> str:
        """加载 Word 文档"""
        try:
            from docx import Document
            
            doc = Document(file_path)
            content = ""
            
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    content += paragraph.text + "\n"
            
            return content
            
        except ImportError:
            logger.error("[DocLoader] python-docx 未安装，请运行: pip install python-docx")
            return ""
        except Exception as e:
            logger.error(f"[DocLoader] DOCX 加载失败: {e}")
            return ""
    
    def _split_text(self, text: str) -> List[str]:
        """
        通用文本分块（适用于 md/txt/pdf）
        
        Args:
            text: 原始文本
            
        Returns:
            文本块列表
        """
        if not text or not text.strip():
            return []
        
        text = text.strip()
        
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        
        # 按段落分割
        paragraphs = re.split(r'\n\s*\n', text)
        
        current_chunk = ""
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            if len(current_chunk) + len(paragraph) + 1 <= self.chunk_size:
                current_chunk = current_chunk + "\n\n" + paragraph if current_chunk else paragraph
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                
                if len(paragraph) > self.chunk_size:
                    sentences = re.split(r'([。！？.!?])', paragraph)
                    current_chunk = ""
                    
                    for i in range(0, len(sentences), 2):
                        sentence = sentences[i]
                        if i + 1 < len(sentences):
                            sentence += sentences[i + 1]
                        
                        if len(current_chunk) + len(sentence) <= self.chunk_size:
                            current_chunk += sentence
                        else:
                            if current_chunk:
                                chunks.append(current_chunk)
                            current_chunk = sentence
                else:
                    current_chunk = paragraph
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _split_legal_document(self, text: str) -> List[str]:
        """
        法律文档专用分块策略
        按条款分割，保持法律条文的完整性
        
        Args:
            text: 原始文本
            
        Returns:
            文本块列表
        """
        if not text or not text.strip():
            return []
        
        text = text.strip()
        
        # 法律文档切割长度（更大，保持上下文）
        legal_chunk_size = 1000
        
        if len(text) <= legal_chunk_size:
            return [text]
        
        chunks = []
        
        # 按法律条款分割（第X条、第X章等）
        # 匹配：第X条、第X章、第X节
        clause_pattern = r'(?=第[一二三四五六七八九十百千\d]+[条章节])'
        clauses = re.split(clause_pattern, text)
        
        current_chunk = ""
        
        for clause in clauses:
            clause = clause.strip()
            if not clause:
                continue
            
            if len(current_chunk) + len(clause) + 1 <= legal_chunk_size:
                current_chunk = current_chunk + "\n" + clause if current_chunk else clause
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                
                # 如果单个条款超过限制，按句号分割
                if len(clause) > legal_chunk_size:
                    sentences = re.split(r'([。])', clause)
                    current_chunk = ""
                    
                    for i in range(0, len(sentences), 2):
                        sentence = sentences[i]
                        if i + 1 < len(sentences):
                            sentence += sentences[i + 1]
                        
                        if len(current_chunk) + len(sentence) <= legal_chunk_size:
                            current_chunk += sentence
                        else:
                            if current_chunk:
                                chunks.append(current_chunk)
                            current_chunk = sentence
                else:
                    current_chunk = clause
        
        if current_chunk:
            chunks.append(current_chunk)
        
        logger.info(f"[DocLoader] 法律文档分块完成，块数: {len(chunks)}，块大小: {legal_chunk_size}")
        return chunks
    
    def get_supported_formats(self) -> List[str]:
        """获取支持的文件格式"""
        return list(self.SUPPORTED_FORMATS)
