import json
import os
from typing import Dict, List, Any, Union


def load_electron_api(json_path: str = None) -> Dict[str, Any]:
    """
    Electronドキュメントの構造化JSONデータをロードします。
    
    Args:
        json_path (str): JSONファイルのパス。デフォルトは'electron-api.json'
        
    Returns:
        Dict[str, Any]: Electron APIドキュメントのJSONオブジェクト
    """
    if json_path is None:
        # デフォルトでプロジェクトルートの electron-api.json を使用
        json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                "electron-api.json")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        electron_api = json.load(f)
    
    return electron_api


def chunk_electron_api(electron_api: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Electron APIドキュメントを検索用チャンクに分割します。
    モジュール、クラス、メソッド単位に分割します。
    
    Args:
        electron_api (Dict[str, Any]): Electron APIのJSONオブジェクト
        
    Returns:
        List[Dict[str, Any]]: 検索用チャンクのリスト
    """
    chunks = []
    
    # APIドキュメント全体をチャンクに分割
    for module in electron_api:
        # モジュールレベルのチャンク
        module_chunk = {
            'type': 'module',
            'name': module.get('name', ''),
            'description': module.get('description', ''),
            'content': f"{module.get('name', '')}: {module.get('description', '')}",
            'source': f"Module: {module.get('name', '')}"
        }
        chunks.append(module_chunk)
        
        # メソッドのチャンク
        if 'methods' in module:
            for method in module['methods']:
                method_chunk = {
                    'type': 'method',
                    'name': f"{module.get('name', '')}.{method.get('name', '')}",
                    'description': method.get('description', ''),
                    'signature': method.get('signature', ''),
                    'content': f"{module.get('name', '')}.{method.get('name', '')} - {method.get('description', '')}",
                    'source': f"Method: {module.get('name', '')}.{method.get('name', '')}"
                }
                chunks.append(method_chunk)
        
        # プロパティのチャンク
        if 'properties' in module:
            for prop in module['properties']:
                prop_chunk = {
                    'type': 'property',
                    'name': f"{module.get('name', '')}.{prop.get('name', '')}",
                    'description': prop.get('description', ''),
                    'content': f"{module.get('name', '')}.{prop.get('name', '')} - {prop.get('description', '')}",
                    'source': f"Property: {module.get('name', '')}.{prop.get('name', '')}"
                }
                chunks.append(prop_chunk)
        
        # イベントのチャンク
        if 'events' in module:
            for event in module['events']:
                event_chunk = {
                    'type': 'event',
                    'name': f"{module.get('name', '')}.{event.get('name', '')}",
                    'description': event.get('description', ''),
                    'content': f"{module.get('name', '')}.{event.get('name', '')} - {event.get('description', '')}",
                    'source': f"Event: {module.get('name', '')}.{event.get('name', '')}"
                }
                chunks.append(event_chunk)
    
    return chunks


if __name__ == "__main__":
    # データロードのテスト
    electron_api = load_electron_api()
    print(f"Loaded {len(electron_api)} modules from Electron API JSON")
    
    chunks = chunk_electron_api(electron_api)
    print(f"Generated {len(chunks)} chunks for search")