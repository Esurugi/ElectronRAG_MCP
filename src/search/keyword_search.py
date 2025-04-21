import math
import re
import string
from collections import Counter
from typing import List, Dict, Any, Set, Tuple, Optional


class BM25:
    """
    BM25アルゴリズムを使用したキーワード検索の実装
    """
    def __init__(
        self, 
        k1: float = 1.5, 
        b: float = 0.75,
        use_stopwords: bool = True,
        max_df: float = 0.85,
        min_df: int = 2
    ):
        """
        BM25パラメータを初期化します。
        
        Args:
            k1 (float): 単語の頻度に関するパラメータ。大きい値は頻度への重みが増す。
            b (float): 文書の長さに関する正規化パラメータ (0 <= b <= 1)
            use_stopwords (bool): ストップワードを除去するかどうか
            max_df (float): この割合より多くの文書に出現する単語を無視する閾値（0.0〜1.0）
            min_df (int): これより少ない文書にしか出現しない単語を無視する閾値
        """
        self.k1 = k1
        self.b = b
        self.use_stopwords = use_stopwords
        self.max_df = max_df
        self.min_df = min_df
        
        self.documents = []
        self.term_freq = []
        self.doc_len = []
        self.avg_doc_len = 0
        self.vocab = set()
        self.idf = {}
        self.doc_count = 0
        
        # 英語のストップワードリスト（必要に応じて日本語も追加可能）
        self._stopwords = {
            'a', 'an', 'the', 'and', 'or', 'but', 'if', 'because', 'as', 'what',
            'which', 'this', 'that', 'these', 'those', 'then', 'just', 'so', 'than', 'such',
            'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more',
            'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same',
            'so', 'than', 'too', 'very', 'can', 'will', 'just', 'should', 'now'
        }
    
    def tokenize(self, text: str) -> List[str]:
        """
        テキストをトークン化します。
        
        Args:
            text (str): トークン化するテキスト
            
        Returns:
            List[str]: トークンのリスト
        """
        if not text:
            return []
            
        try:
            # 小文字に変換
            text = text.lower()
            # 句読点を削除
            text = re.sub(f'[{re.escape(string.punctuation)}]', ' ', text)
            # 空白で分割
            tokens = text.split()
            
            # ストップワードを除去（設定されている場合）
            if self.use_stopwords:
                tokens = [token for token in tokens if token not in self._stopwords]
                
            return tokens
        except Exception as e:
            print(f"トークン化エラー: {e}")
            return []
    
    def add_documents(self, documents: List[Dict[str, Any]], content_field: str = 'content'):
        """
        検索するドキュメントを追加します。
        
        Args:
            documents (List[Dict[str, Any]]): ドキュメントのリスト
            content_field (str): ドキュメントから検索対象テキストを取得するフィールド名
        """
        if not documents:
            return
            
        self.documents = documents
        self.doc_count = len(documents)
        self.term_freq = []
        self.doc_len = []
        self.vocab = set()
        
        # 各ドキュメントのトークン頻度を計算
        term_doc_freq = Counter()  # 単語の文書頻度カウンター
        
        for doc in documents:
            content = doc.get(content_field, "")
            tokens = self.tokenize(content)
            self.doc_len.append(len(tokens))
            term_freq = {}
            
            # 各単語の出現回数をカウント
            for token in tokens:
                term_freq[token] = term_freq.get(token, 0) + 1
                self.vocab.add(token)
            
            # 各単語が出現する文書数を更新
            for token in set(tokens):  # 重複を除いたトークン
                term_doc_freq[token] += 1
            
            self.term_freq.append(term_freq)
        
        # 平均ドキュメント長を計算
        self.avg_doc_len = sum(self.doc_len) / self.doc_count if self.doc_count > 0 else 0
        
        # 単語のフィルタリング（高頻度/低頻度の単語を除外）
        filtered_vocab = set()
        for term, doc_freq in term_doc_freq.items():
            # 出現文書率が max_df 以下かつ出現文書数が min_df 以上の単語を保持
            if (doc_freq / self.doc_count <= self.max_df) and (doc_freq >= self.min_df):
                filtered_vocab.add(term)
        
        # フィルタリングされた語彙に更新
        self.vocab = filtered_vocab
        
        # IDFを計算
        self.idf = {}
        for term in self.vocab:
            df = term_doc_freq[term]
            # IDF値の計算（Robertson-Spärck Jones式）
            self.idf[term] = math.log((self.doc_count - df + 0.5) / (df + 0.5) + 1)
    
    def get_top_terms(self, query: str, top_n: int = 5) -> List[Tuple[str, float]]:
        """
        クエリから重要な単語とそのIDFスコアを取得します。
        
        Args:
            query (str): 検索クエリ
            top_n (int): 返す単語の数
            
        Returns:
            List[Tuple[str, float]]: (単語, IDFスコア) のリスト
        """
        query_tokens = self.tokenize(query)
        term_scores = [(token, self.idf.get(token, 0)) for token in query_tokens if token in self.vocab]
        term_scores.sort(key=lambda x: x[1], reverse=True)
        return term_scores[:top_n]
    
    def search(self, query: str, top_k: int = 10, min_score: float = 0.0) -> List[Dict[str, Any]]:
        """
        クエリに最も関連するドキュメントを検索します。
        
        Args:
            query (str): 検索クエリ
            top_k (int): 返す結果の最大数
            min_score (float): この値以上のスコアを持つ結果のみ返す
            
        Returns:
            List[Dict[str, Any]]: 検索結果とBM25スコアのリスト
        """
        if not self.documents or not query:
            return []
        
        try:
            # クエリをトークン化
            query_tokens = self.tokenize(query)
            
            # クエリに有効なトークンがない場合は空のリストを返す
            valid_tokens = [token for token in query_tokens if token in self.vocab]
            if not valid_tokens:
                return []
            
            # 各ドキュメントのBM25スコアを計算
            scores = []
            for i, doc_tf in enumerate(self.term_freq):
                score = 0
                doc_len = self.doc_len[i]
                
                for token in valid_tokens:
                    # BM25スコア計算式
                    tf = doc_tf.get(token, 0)
                    if tf > 0:  # tf > 0の場合のみ計算（最適化）
                        numerator = tf * (self.k1 + 1)
                        denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_len)
                        token_score = self.idf.get(token, 0) * (numerator / denominator)
                        score += token_score
                
                if score > min_score:  # 最小スコアでフィルタリング
                    scores.append((i, score))
            
            # スコアでソート
            scores.sort(key=lambda x: x[1], reverse=True)
            
            # 結果を整形
            results = []
            for i, score in scores[:top_k]:
                doc = self.documents[i].copy()
                doc['score'] = float(score)
                # 重要な単語をマーキング（オプション）
                # doc['matched_terms'] = [token for token in valid_tokens if token in self.term_freq[i]]
                results.append(doc)
            
            return results
            
        except Exception as e:
            print(f"検索エラー: {e}")
            return []