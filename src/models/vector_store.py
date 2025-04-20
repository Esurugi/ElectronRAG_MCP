from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
import numpy as np
import os
import json
import faiss
import pickle


class VectorEmbedder:
    """
    Sentence Transformers を使用してテキストのベクトル埋め込みを行うクラス
    """
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Sentence Transformers モデルを初期化します。
        
        Args:
            model_name (str): 使用するモデル名
        """
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
    
    def embed_text(self, text: str) -> np.ndarray:
        """
        テキストのベクトル埋め込みを生成します。
        
        Args:
            text (str): 埋め込みを生成するテキスト
            
        Returns:
            np.ndarray: 埋め込みベクトル
        """
        return self.model.encode(text)
    
    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """
        複数のテキストのベクトル埋め込みをバッチ処理で生成します。
        
        Args:
            texts (List[str]): 埋め込みを生成するテキストのリスト
            
        Returns:
            np.ndarray: 埋め込みベクトルの配列
        """
        return self.model.encode(texts, show_progress_bar=True)


class FAISSVectorStore:
    """
    FAISSを使用したベクトルストアの実装
    """
    def __init__(self, embedding_dim: int = 384):
        """
        FAISS インデックスを初期化します。
        
        Args:
            embedding_dim (int): 埋め込みベクトルの次元数
        """
        self.index = faiss.IndexFlatL2(embedding_dim)
        self.documents = []
        self.embedding_dim = embedding_dim
    
    def add_documents(self, documents: List[Dict[str, Any]], embeddings: np.ndarray):
        """
        ドキュメントとその埋め込みをインデックスに追加します。
        
        Args:
            documents (List[Dict[str, Any]]): ドキュメントのリスト
            embeddings (np.ndarray): ドキュメントに対応する埋め込みベクトル
        """
        if len(documents) != embeddings.shape[0]:
            raise ValueError(f"Documents length ({len(documents)}) and embeddings length ({embeddings.shape[0]}) must match")
        
        # FAISSインデックスに追加
        self.index.add(embeddings)
        self.documents.extend(documents)
    
    def search(self, query_embedding: np.ndarray, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        クエリ埋め込みに最も類似したドキュメントを検索します。
        
        Args:
            query_embedding (np.ndarray): クエリの埋め込みベクトル
            top_k (int): 返す結果の最大数
            
        Returns:
            List[Dict[str, Any]]: 検索結果と類似度スコアのリスト
        """
        if self.index.ntotal == 0:
            return []
        
        # クエリを正規化して検索
        if len(query_embedding.shape) == 1:
            query_embedding = query_embedding.reshape(1, -1)
        
        # 検索を実行
        distances, indices = self.index.search(query_embedding, min(top_k, self.index.ntotal))
        
        # 結果を整形
        results = []
        for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
            if idx < len(self.documents) and idx >= 0:
                doc = self.documents[idx].copy()
                doc['score'] = float(1.0 / (1.0 + dist))  # L2距離を類似度スコアに変換
                results.append(doc)
        
        return results
    
    def save(self, directory: str):
        """
        FAISSインデックスとドキュメントをディスクに保存します。
        
        Args:
            directory (str): 保存先ディレクトリ
        """
        os.makedirs(directory, exist_ok=True)
        
        # インデックスを保存
        faiss.write_index(self.index, os.path.join(directory, "faiss_index.bin"))
        
        # ドキュメントを保存
        with open(os.path.join(directory, "documents.pkl"), 'wb') as f:
            pickle.dump(self.documents, f)
    
    @classmethod
    def load(cls, directory: str):
        """
        FAISSインデックスとドキュメントをディスクから読み込みます。
        
        Args:
            directory (str): 読み込み元ディレクトリ
            
        Returns:
            FAISSVectorStore: 読み込んだベクトルストア
        """
        # インスタンスを作成
        vector_store = cls()
        
        # インデックスを読み込み
        vector_store.index = faiss.read_index(os.path.join(directory, "faiss_index.bin"))
        
        # ドキュメントを読み込み
        with open(os.path.join(directory, "documents.pkl"), 'rb') as f:
            vector_store.documents = pickle.load(f)
        
        return vector_store