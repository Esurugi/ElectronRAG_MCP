from typing import List, Dict, Any, Optional, Tuple, Union
import numpy as np
import hashlib
from sentence_transformers.cross_encoder import CrossEncoder

from src.models.vector_store import VectorEmbedder, FAISSVectorStore
from src.search.keyword_search import BM25


def normalize_scores(results: List[Dict[str, Any]], score_key: str = 'score') -> List[Dict[str, Any]]:
    """
    検索結果のスコアをMin-Max正規化します。
    
    Args:
        results (List[Dict[str, Any]]): 検索結果のリスト
        score_key (str): スコアのキー名
        
    Returns:
        List[Dict[str, Any]]: 正規化された検索結果のリスト
    """
    if not results:
        return results
        
    # スコア抽出
    scores = [doc.get(score_key, 0.0) for doc in results]
    min_score, max_score = min(scores), max(scores)
    
    # スコアレンジが狭い場合は正規化不要
    if max_score - min_score < 1e-9:
        return results
    
    # スコア正規化
    for doc in results:
        if score_key in doc:
            doc[score_key] = (doc[score_key] - min_score) / (max_score - min_score)
    
    return results


def generate_doc_id(doc: Dict[str, Any], idx: int = None) -> str:
    """
    ドキュメントから一意のIDを生成します。
    
    Args:
        doc (Dict[str, Any]): ドキュメント
        idx (int, optional): ドキュメントのインデックス
        
    Returns:
        str: 一意のドキュメントID
    """
    # ドキュメント名をベースにする
    base_id = doc.get('name', '')
    
    # 内容のハッシュを常に生成（一意性を保証するため）
    content = doc.get('content', '')
    content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()[:8]
    
    # インデックスがある場合は追加
    suffix = f"#{idx}" if idx is not None else ""
    
    # 名前_コンテンツハッシュ#インデックス の形式で返す
    return f"{base_id}_{content_hash}{suffix}"


def rrf_fusion(result_lists: List[List[Dict[str, Any]]], k: int = 60) -> List[Dict[str, Any]]:
    """
    Reciprocal Rank Fusion (RRF) アルゴリズムを使用して、複数の検索結果をマージします。
    
    Args:
        result_lists (List[List[Dict[str, Any]]]): 複数の検索エンジンからの結果リスト
        k (int): RRF定数
        
    Returns:
        List[Dict[str, Any]]: マージされた結果リスト
    """
    # 空の結果リストを除外
    result_lists = [results for results in result_lists if results]
    if not result_lists:
        return []
    
    # ドキュメントID -> RRFスコアのマッピング
    rrf_scores = {}
    
    # 各結果リストから、ドキュメントのランクを取得
    for list_idx, results in enumerate(result_lists):
        for rank, doc in enumerate(results):
            # ドキュメントの一意識別子を生成（名前とインデックスを組み合わせる）
            doc_id = generate_doc_id(doc)
            
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
        use_rrf: bool = True,
        reranker_batch_size: int = 16
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
            reranker_batch_size (int): 再ランキングのバッチサイズ
        """
        self.alpha = alpha
        self.use_reranker = use_reranker
        self.use_rrf = use_rrf
        self.reranker_batch_size = reranker_batch_size
        
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
            # ベクトル検索結果のスコアを正規化
            vector_results = normalize_scores(vector_results)
        
        # キーワード検索
        keyword_results = []
        if self.alpha < 1.0:
            keyword_results = self.keyword_search.search(query, top_k=top_k * 2)
            # キーワード検索結果のスコアを正規化
            keyword_results = normalize_scores(keyword_results)
        
        # 結果の統合
        if self.use_rrf:
            # RRFで結果を融合
            results = rrf_fusion([vector_results, keyword_results])
        else:
            # alpha加重平均でスコアを計算（正規化済みスコアを使用）
            result_dict = {}
            
            # 一意のドキュメントIDを生成して結果を処理
            for i, doc in enumerate(vector_results):
                doc_id = generate_doc_id(doc, i)
                if doc_id not in result_dict:
                    result_dict[doc_id] = {
                        'document': doc,
                        'vector_score': 0.0,
                        'keyword_score': 0.0
                    }
                result_dict[doc_id]['vector_score'] = doc['score']
            
            for i, doc in enumerate(keyword_results):
                doc_id = generate_doc_id(doc, i)
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
                # alpha加重平均（両スコアは既に0-1に正規化済み）
                doc['score'] = self.alpha * info['vector_score'] + (1 - self.alpha) * info['keyword_score']
                results.append(doc)
            
            # スコアでソート
            results.sort(key=lambda x: x['score'], reverse=True)
        
        # 再ランキングが有効な場合
        if self.use_reranker and self.reranker and results:
            # 上位N件を再ランキング
            top_results = results[:min(rerank_top_k, len(results))]
            
            # クエリとドキュメントのペアを作成
            pairs = [(query, doc['content']) for doc in top_results]
            
            try:
                # バッチ処理でメモリ効率を向上
                rerank_scores = []
                batch_size = self.reranker_batch_size
                
                for i in range(0, len(pairs), batch_size):
                    batch_pairs = pairs[i:i + batch_size]
                    batch_scores = self.reranker.predict(batch_pairs)
                    rerank_scores.extend(batch_scores)
                
                # 結果とスコアを組み合わせて再ソート
                for i, score in enumerate(rerank_scores):
                    top_results[i]['score'] = float(score)
                
                # 再ランキング結果をスコア正規化
                top_results = normalize_scores(top_results)
                
                # スコアでソート
                reranked_results = sorted(top_results, key=lambda x: x['score'], reverse=True)
                
                # 再ランキングした結果とそれ以外を組み合わせ
                final_results = reranked_results + results[rerank_top_k:]
            except Exception as e:
                print(f"再ランキング中にエラーが発生しました: {e}")
                # エラーが発生した場合は、元の結果を使用
                final_results = results
        else:
            final_results = results
        
        # 上位K件を返す
        return final_results[:top_k]