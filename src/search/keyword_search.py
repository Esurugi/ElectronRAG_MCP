import math
import re
import string
from collections import Counter
from typing import List, Dict, Any, Set, Tuple


class BM25:
    """
    BM25アルゴリズムを使用したキーワード検索の実装
    """
    def __init__(self, k1=1.5, b=0.75):
        """
        BM25パラメータを初期化します。
        
        Args:
            k1 (float): 単語の頻度に関するパラメータ。大きい値は頻度への重みが増す。
            b (float): 文書の長さに関する正規化パラメータ (0 <= b <= 1)
        """
        self.k1 = k1
        self.b = b
        self.documents = []
        self.term_freq = []
        self.doc_len = []
        self.avg_doc_len = 0
        self.vocab = set()
        self.idf = {}
        self.doc_count = 0
    
    def tokenize(self, text: str) -> List[str]:
        """
        テキストをトークン化します。
        
        Args:
            text (str): トークン化するテキスト
            
        Returns:
            List[str]: トークンのリスト
        """
        # 小文字に変換
        text = text.lower()
        # 句読点を削除
        text = re.sub(f'[{re.escape(string.punctuation)}]', ' ', text)
        # 空白で分割
        return text.split()
    
    def add_documents(self, documents: List[Dict[str, Any]], content_field: str = 'content'):
        """
        検索するドキュメントを追加します。
        
        Args:
            documents (List[Dict[str, Any]]): ドキュメントのリスト
            content_field (str): ドキュメントから検索対象テキストを取得するフィールド名
        """
        self.documents = documents
        self.doc_count = len(documents)
        
        # 各ドキュメントのトークン頻度を計算
        for doc in documents:
            tokens = self.tokenize(doc[content_field])
            self.doc_len.append(len(tokens))
            term_freq = {}
            
            for token in tokens:
                self.vocab.add(token)
                term_freq[token] = term_freq.get(token, 0) + 1
            
            self.term_freq.append(term_freq)
        
        # 平均ドキュメント長を計算
        self.avg_doc_len = sum(self.doc_len) / self.doc_count if self.doc_count > 0 else 0
        
        # IDFを計算
        self.idf = {}
        for term in self.vocab:
            df = sum(1 for doc_tf in self.term_freq if term in doc_tf)
            # IDF値の計算に+1を使って0除算を回避
            self.idf[term] = math.log((self.doc_count - df + 0.5) / (df + 0.5) + 1)
    
    def search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        クエリに最も関連するドキュメントを検索します。
        
        Args:
            query (str): 検索クエリ
            top_k (int): 返す結果の最大数
            
        Returns:
            List[Dict[str, Any]]: 検索結果とBM25スコアのリスト
        """
        if not self.documents:
            return []
        
        # クエリをトークン化
        query_tokens = self.tokenize(query)
        
        # 各ドキュメントのBM25スコアを計算
        scores = []
        for i, doc_tf in enumerate(self.term_freq):
            score = 0
            doc_len = self.doc_len[i]
            
            for token in query_tokens:
                if token not in self.vocab:
                    continue
                
                # BM25スコア計算式
                tf = doc_tf.get(token, 0)
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_len)
                score += self.idf.get(token, 0) * (numerator / denominator)
            
            scores.append((i, score))
        
        # スコアでソート
        scores.sort(key=lambda x: x[1], reverse=True)
        
        # 結果を整形
        results = []
        for i, score in scores[:top_k]:
            if score > 0:  # スコアが0より大きい結果のみ返す
                doc = self.documents[i].copy()
                doc['score'] = float(score)
                results.append(doc)
        
        return results