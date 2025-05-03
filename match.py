import difflib
import pandas as pd
from typing import List, Dict

def match_things(key_word: str, search_type: str, num: int, rate: float) -> pd.DataFrame:
    """
    改进的模糊匹配函数，支持多种搜索类型
    :param key_word: 搜索关键词
    :param search_type: 搜索类型(论文/作者/期刊/关键词/机构/技术领域)
    :param num: 返回结果数量
    :param rate: 相似度阈值
    :return: 包含匹配结果的DataFrame
    """
    # 映射前端搜索类型到实体类型
    type_mapping = {
        '论文': 'art',
        '作者': 'aut',
        '期刊': 'jou',
        '关键词': 'key',
        '机构': 'ins',
        '技术领域': 'dom'
    }
    
    try:
        entity_type = type_mapping.get(search_type)
        if not entity_type:
            return pd.DataFrame({search_type: []})
            
        entity_list = load_enti_list(entity_type)
        
        # 改进的模糊匹配逻辑
        if search_type == '关键词':
            # 对关键词采用更宽松的匹配方式
            matches = []
            for word in entity_list:
                if key_word.lower() in word.lower():
                    similarity = difflib.SequenceMatcher(None, key_word.lower(), word.lower()).ratio()
                    if similarity >= rate:
                        matches.append((word, similarity))
            
            # 按相似度排序并取前num个
            matches.sort(key=lambda x: x[1], reverse=True)
            simi = [match[0] for match in matches[:num]]
        else:
            # 其他类型使用标准模糊匹配
            simi = difflib.get_close_matches(
                key_word, 
                entity_list, 
                n=num, 
                cutoff=rate
            )
        
        return pd.DataFrame({search_type: simi if simi else ["未找到匹配结果"]})
        
    except Exception as e:
        print(f"匹配出错: {str(e)}")
        return pd.DataFrame({search_type: ["匹配过程中出错"]})

def load_enti_list(name: str) -> List[str]:
    """
    加载实体列表文件
    :param name: 实体类型简写(art/aut/jou/key/ins/dom)
    :return: 实体列表
    """
    try:
        file_path = f'./data/word_dic/{name}.txt'
        with open(file_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"警告: 未找到实体文件 {file_path}")
        return []
    except Exception as e:
        print(f"加载实体列表出错: {str(e)}")
        return []