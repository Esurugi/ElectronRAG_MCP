import sys
import time
import json
from src.search.hybrid_search import HybridSearcher
from src.utils.load_data import load_electron_api, chunk_electron_api


def test_normalize_scores():
    """スコア正規化関数のテスト"""
    from src.search.hybrid_search import normalize_scores
    
    # テスト用データ
    test_results = [
        {'name': 'doc1', 'score': 0.9},
        {'name': 'doc2', 'score': 0.5},
        {'name': 'doc3', 'score': 0.1}
    ]
    
    # 正規化実行
    normalized = normalize_scores(test_results)
    
    # 結果の確認
    min_score, max_score = min(r['score'] for r in normalized), max(r['score'] for r in normalized)
    print(f"スコア正規化テスト: 最小={min_score}, 最大={max_score}")
    print(f"正規化結果: {[r['score'] for r in normalized]}")
    
    # 期待値: 最小値は0、最大値は1
    assert abs(min_score - 0.0) < 0.001
    assert abs(max_score - 1.0) < 0.001
    
    return True


def test_generate_doc_id():
    """ドキュメントID生成関数のテスト"""
    from src.search.hybrid_search import generate_doc_id
    
    # テスト用データ
    doc1 = {'name': 'test', 'content': 'This is a test'}
    doc2 = {'name': 'test', 'content': 'This is another test'}
    
    # ID生成
    id1 = generate_doc_id(doc1)
    id2 = generate_doc_id(doc2)
    id1_with_idx = generate_doc_id(doc1, 1)
    
    print(f"ID生成テスト: id1={id1}")
    print(f"ID生成テスト: id2={id2}")
    print(f"ID生成テスト (インデックス付き): id1_with_idx={id1_with_idx}")
    
    # 同じ名前でも内容が異なればIDは異なるはず
    assert id1 != id2, "内容が異なる場合はIDも異なるべき"
    # インデックスを指定するとIDは異なるはず
    assert id1 != id1_with_idx, "インデックスを指定するとIDは異なるべき"
    
    return True


def test_hybrid_search():
    """ハイブリッド検索のテスト"""
    # サンプルデータの読み込み
    try:
        print("Electronデータを読み込み中...")
        api_json = load_electron_api("electron-api.json")
        print(f"APIドキュメント読み込み完了: {len(api_json)} モジュール")
        
        # チャンキング
        print("チャンキング実行中...")
        start_time = time.time()
        chunks = chunk_electron_api(api_json)
        print(f"{len(chunks)}個のチャンク生成 ({time.time() - start_time:.2f}秒)")
        
        # ハイブリッド検索初期化（少数のチャンクのみ使用）
        print("ハイブリッド検索エンジン初期化中...")
        test_chunks = chunks[:100]  # テスト用に最初の100チャンクのみ使用
        
        # 改善したHybridSearcherを初期化
        searcher = HybridSearcher(
            documents=test_chunks,
            alpha=0.7,
            use_reranker=True,
            use_rrf=True,
            reranker_batch_size=8
        )
        
        # 検索実行
        print("検索実行: 'window create'...")
        start_time = time.time()
        results = searcher.search("window create", top_k=5)
        search_time = time.time() - start_time
        
        # 結果表示
        print(f"\n検索完了: {len(results)}件 ({search_time:.2f}秒)")
        for i, doc in enumerate(results, 1):
            print(f"{i}. {doc['name']} (スコア: {doc['score']:.4f})")
            print(f"   種類: {doc['type']}")
            print(f"   説明: {doc.get('description', '')[:100]}...")
        
        # RRF無しでのテスト
        print("\nRRFなし (alpha加重平均) での検索: 'window create'...")
        searcher.use_rrf = False
        start_time = time.time()
        results_no_rrf = searcher.search("window create", top_k=5)
        search_time = time.time() - start_time
        
        print(f"\n検索完了: {len(results_no_rrf)}件 ({search_time:.2f}秒)")
        for i, doc in enumerate(results_no_rrf, 1):
            print(f"{i}. {doc['name']} (スコア: {doc['score']:.4f})")
            print(f"   種類: {doc['type']}")
            print(f"   説明: {doc.get('description', '')[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"エラー発生: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_bm25_improvements():
    """改善されたBM25の機能テスト"""
    from src.search.keyword_search import BM25
    
    # テスト用のサンプルドキュメント
    test_docs = [
        {"name": "doc1", "content": "The quick brown fox jumps over the lazy dog"},
        {"name": "doc2", "content": "A quick brown fox jumps over a lazy dog"},
        {"name": "doc3", "content": "The lazy dog sleeps all day"},
        {"name": "doc4", "content": "Quick foxes are known for jumping high"},
        {"name": "doc5", "content": "Dogs are man's best friend"}
    ]
    
    print("\nBM25改善テスト...")
    
    # ストップワードなしBM25
    bm25_no_stop = BM25(use_stopwords=False)
    bm25_no_stop.add_documents(test_docs)
    
    # ストップワード有りBM25
    bm25_with_stop = BM25(use_stopwords=True)
    bm25_with_stop.add_documents(test_docs)
    
    query = "the quick fox"
    
    # 検索実行
    results_no_stop = bm25_no_stop.search(query)
    results_with_stop = bm25_with_stop.search(query)
    
    # 結果表示
    print("\nストップワードなしの結果:")
    for i, doc in enumerate(results_no_stop, 1):
        print(f"{i}. {doc['name']} (スコア: {doc['score']:.4f}): {doc['content']}")
    
    print("\nストップワード有りの結果:")
    for i, doc in enumerate(results_with_stop, 1):
        print(f"{i}. {doc['name']} (スコア: {doc['score']:.4f}): {doc['content']}")
    
    # 重要単語抽出テスト
    top_terms = bm25_with_stop.get_top_terms(query, top_n=3)
    print(f"\n重要単語: {top_terms}")
    
    return True


def main():
    """すべてのテストを実行"""
    tests = [
        ("スコア正規化テスト", test_normalize_scores),
        ("ドキュメントID生成テスト", test_generate_doc_id),
        ("BM25改善テスト", test_bm25_improvements),
        ("ハイブリッド検索テスト", test_hybrid_search)
    ]
    
    results = []
    
    for name, test_func in tests:
        print(f"\n===== {name} 開始 =====")
        try:
            success = test_func()
            results.append((name, success))
            print(f"===== {name}: {'成功' if success else '失敗'} =====\n")
        except Exception as e:
            print(f"テスト中にエラー発生: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
            print(f"===== {name}: 失敗 =====\n")
    
    # 結果のサマリー
    print("\n===== テスト結果サマリー =====")
    for name, success in results:
        print(f"{name}: {'✓ 成功' if success else '✗ 失敗'}")
    
    # 全体の成功/失敗
    if all(success for _, success in results):
        print("\n全テスト成功! リファクタリングは正常に機能しています。")
        return 0
    else:
        print("\n一部のテストが失敗しました。詳細なエラーメッセージを確認してください。")
        return 1


if __name__ == "__main__":
    sys.exit(main())