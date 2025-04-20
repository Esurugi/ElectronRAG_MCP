from typing import List, Dict, Any, Optional, Tuple, Union
import numpy as np
from sentence_transformers.cross_encoder import CrossEncoder

from src.models.vector_store import VectorEmbedder, FAISSVectorStore
from src.search.keyword_search import BM25


def rrf_fusion(result_lists: List[List[Dict[str, Any]]], k: int = 60) -> List[Dict[str, Any]]:
    """
    Reciprocal Rank Fusion (RRF) アルゴリズムを使用して、複数の検索結果をマージします。
    
    Args:
        result_lists (List[List[Dict[str, Any]]]): 複数の検索エンジンからの結果リスト
        k (int): RRF定数
        
    Returns:
        List[Dict[str, Any]]: マージされた結果リスト
    """
    # ドキュメントID -> RRFスコアのマッピング
    rrf_scores = {}
    
    # 各結果リストから、ドキュメントのランクを取得
    for results in result_lists:
        for rank, doc in enumerate(results):
            doc_id = doc.get('name', '')  # ドキュメントの一意識別子
            
            # 同じドキュメントが複数の結果セットに出現する場合
            if doc_id not in rrf_scores:
                rrf_scores[doc_id] = {
                    'document': doc,
                    'score': 0
                }
            
            # RRFスコアを加算 (1 / (rank + k))
            rrf_scores[doc_id]['score'] += 1.0 / (rank + k)
    
    # RRFスコアでソート
    merged_results = [
        {**item['document'], 'score': float(item['score'])}
        for item in sorted(rrf_scores.values(), key=lambda x: x['score'], reverse=True)
    ]
    
    return merged_results


class HybridSearcher:
    """
    ベクトル検索とキーワード検索を組み合わせたハイブリッド検索を実装するクラス
    """
    def __init__(
        self, 
        documents: List[Dict[str, Any]] = None,
        alpha: float = 0.7,
        use_reranker: bool = True,
        reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        use_rrf: bool = True
    ):
        """
        ハイブリッド検索エンジンを初期化します。
        
        Args:
            documents (List[Dict[str, Any]]): 検索対象ドキュメント
            alpha (float): ベクトル検索とキーワード検索の重み付け (0.0 <= alpha <= 1.0)
                          1.0はベクトル検索のみ、0.0はキーワード検索のみ
            use_reranker (bool): 再ランキングを使用するかどうか
            reranker_model (str): 再ランキング用のCross-Encoderモデル名
            use_rrf (bool): 結果融合にRRFを使用するかどうか (Falseの場合はalpha加重平均を使用)
        """
        self.alpha = alpha
        self.use_reranker = use_reranker
        self.use_rrf = use_rrf
        
        # 埋め込みモデル
        self.embedder = VectorEmbedder()
        
        # ベクトル検索エンジン
        self.vector_store = FAISSVectorStore(embedding_dim=self.embedder.embedding_dim)
        
        # キーワード検索エンジン
        self.keyword_search = BM25()
        
        # 再ランキングモデル（必要な場合のみ初期化）
        self.reranker = None
        if use_reranker:
            self.reranker = CrossEncoder(reranker_model)
        
        # ドキュメントが提供された場合は追加
        if documents:
            self.add_documents(documents)
    
    def add_documents(self, documents: List[Dict[str, Any]]):
        """
        ドキュメントを検索エンジンに追加します。
        
        Args:
            documents (List[Dict[str, Any]]): 検索対象ドキュメント
        """
        # コンテンツをリストに抽出
        contents = [doc['content'] for doc in documents]
        
        # ベクトル埋め込みを生成
        embeddings = self.embedder.embed_batch(contents)
        
        # ベクトル検索エンジンに追加
        self.vector_store.add_documents(documents, embeddings)
        
        # キーワード検索エンジンに追加
        self.keyword_search.add_documents(documents)
    
    def search(self, query: str, top_k: int = 10, rerank_top_k: int = 50) -> List[Dict[str, Any]]:
        """
        ハイブリッド検索を実行します。
        
        Args:
            query (str): 検索クエリ
            top_k (int): 返す結果の数
            rerank_top_k (int): 再ランキングを行う上位結果の数
            
        Returns:
            List[Dict[str, Any]]: 検索結果のリスト
        """
        # ベクトル検索
        vector_results = []
        if self.alpha > 0:
            query_embedding = self.embedder.embed_text(query)
            vector_results = self.vector_store.search(query_embedding, top_k=top_k * 2)
        
        # キーワード検索
        keyword_results = []
        if self.alpha < 1.0:
            keyword_results = self.keyword_search.search(query, top_k=top_k * 2)
        
        # 結果の統合
        if self.use_rrf:
            # RRFで結果を融合
            results = rrf_fusion([vector_results, keyword_results])
        else:
            # alpha加重平均でスコアを計算
            result_dict = {}
            
            # ベクトル検索の結果を処理
            for doc in vector_results:
                doc_id = doc['name']
                if doc_id not in result_dict:
                    result_dict[doc_id] = {
                        'document': doc,
                        'vector_score': 0.0,
                        'keyword_score': 0.0
                    }
                result_dict[doc_id]['vector_score'] = doc['score']
            
            # キーワード検索の結果を処理
            for doc in keyword_results:
                doc_id = doc['name']
                if doc_id not in result_dict:
                    result_dict[doc_id] = {
                        'document': doc,
                        'vector_score': 0.0,
                        'keyword_score': 0.0
                    }
                result_dict[doc_id]['keyword_score'] = doc['score']
            
            # 最終スコアを計算
            results = []
            for doc_id, info in result_dict.items():
                doc = info['document'].copy()
                # alpha加重平均
                doc['score'] = self.alpha * info['vector_score'] + (1 - self.alpha) * info['keyword_score']
                results.append(doc)
            
            # スコアでソート
            results.sort(key=lambda x: x['score'], reverse=True)
        
        # 再ランキングが有効な場合
        if self.use_reranker and self.reranker:
            # 上位N件を再ランキング
            top_results = results[:min(rerank_top_k, len(results))]
            
            # クエリとドキュメントのペアを作成
            pairs = [(query, doc['content']) for doc in top_results]
            
            # 再ランキングスコアを計算
            rerank_scores = self.reranker.predict(pairs)
            
            # 結果とスコアを組み合わせて再ソート
            for i, score in enumerate(rerank_scores):
                top_results[i]['score'] = float(score)
            
            reranked_results = sorted(top_results, key=lambda x: x['score'], reverse=True)
            
            # 再ランキングした結果とそれ以外を組み合わせ
            final_results = reranked_results + results[rerank_top_k:]
        else:
            final_results = results
        
        # 上位K件を返す
        return final_results[:top_k]