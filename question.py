import re
import jieba
#分词器
jieba.load_userdict(r"./data/word_dic/all.txt")

class question_from_user():#问题类
    def __init__(self, query):
        self.query = query
        # 先获取EN和ques_
        self.li_aut = self.load_enti_list('aut')  # 作者列表
        self.li_jou = self.load_enti_list('jou')  # 期刊列表
        self.li_key = self.load_enti_list('key')  # 关键词列表
        self.li_ins = self.load_enti_list('ins')  # 机构列表
        self.li_dom = self.load_enti_list('dom')  # 领域列表
        self.li_art = self.load_enti_list('art')  # 文章列表
        
        # 修改调用顺序
        self.EN, ques_ = self.get_EN(self.query, self.li_aut, self.li_jou, self.li_key, self.li_ins, self.li_dom)
        self.IR = self.get_IR(ques_)  # 传递ques_参数
        # 移除不存在的get_right_art()调用
        self.simi, self.right_art = self.art_match(self.li_art, self.EN['Article'])  # 相似文章和正确文章

    def load_enti_list(self,name):#读取实体文件
        f = open(r'./data/word_dic/'+name+'.txt','r', encoding='utf-8')
        return f.read().splitlines()    
    
    def get_IR(self, ques):#意图识别
        dic_classes = {    
            'WRITTEN_BY': ['作者是谁', '作者是', '的作者', '谁写的', '撰写了哪些论文'],
            'PUBLISHED_IN': ['期刊','发表在哪一个期刊', '发表期刊', '发表了哪些论文', '刊登于', '发表了什么文章', '发表了哪些文章'],
            'HAS_KEYWORD': ['关键词有', '关键字是', '主题词是','相关论文有哪些'],
            'BELONGS_TO': ['属于哪个领域', '属于哪个分类', '属于哪个类别'],
            'AFFILIATED_WITH': ['哪个机构', '哪个单位', '所属机构', '隶属于', '隶属单位'],
            'SUB_DOMAIN_OF':['中国先进技术','哪几个方面'],
            'abstract': ['摘要是什么', '文章摘要', '论文概要'],
            'isbn_issn': ['ISBN号', 'ISSN号', '编号是'],
            'notes':['notes是什么','Notes内容','刊号分类号'],
            'url': ['网址是什么', '链接地址', 'URL地址'],
            '介绍': ['介绍一下', '详细介绍', '完整信息'],
            }
        all_IR = []
        
        # 先检查特定意图短语
        for i in dic_classes:
            for j in dic_classes[i]:
                if j in ques and i not in all_IR:
                    all_IR.append(i)
        
        # 如果没有识别到特定意图，再检查一般关键词
        if not all_IR:
            general_keywords = {
                'WRITTEN_BY': ['作者', '撰写', '写了', '写作'],
                'PUBLISHED_IN': ['发表', '期刊', '杂志'],
                'HAS_KEYWORD': ['关键词', '关键字', '主题词'],
                'BELONGS_TO': ['领域', '分类', '类别'],
                'AFFILIATED_WITH': ['机构', '单位', '所属'],
                'SUB_DOMAIN_OF':['中国先进技术','哪几个方面'],
                'abstract': ['摘要', '概要'],
                'isbn_issn': ['ISBN', 'ISSN', '编号'],
                'url': ['网址', '链接', 'URL'],
            }
            for i in general_keywords:
                for j in general_keywords[i]:
                    if j in ques and i not in all_IR:
                        all_IR.append(i)
        
        # # 最后检查实体类型
        # if not all_IR and self.EN.get('Author'):
        #     all_IR.append('WRITTEN_BY')
            
        # 修改意图识别优先级，确保BELONGS_TO优先
        if '属于' in ques or '领域' in ques or '分类' in ques:
            if 'BELONGS_TO' not in all_IR:
                all_IR.insert(0, 'BELONGS_TO')  # 确保BELONGS_TO在最前面
                
        return all_IR

    def get_EN(self, ques, li_aut, li_jou, li_key, li_ins, li_dom):
        ques_article = re.findall("《(.*?)》",ques)
        ques = re.sub(r'《.*?》', "",ques)
        ques_word_list = jieba.lcut(ques)
        enti_dicts = {}
        aut_ = []
        jou_ = []
        key_ = []
        ins_ = []
        dom_ = []

        # 特殊处理期刊名称识别
        journal_pattern = r'(期刊|杂志)?([\u4e00-\u9fa5]+(?:\([\u4e00-\u9fa5]+\))?)'
        journal_matches = re.finditer(journal_pattern, ques)
        for match in journal_matches:
            journal_name = match.group(2)
            if journal_name in li_jou:
                jou_.append(journal_name)
                # 从问题中移除已识别的期刊名称，避免重复识别
                ques = ques.replace(journal_name, "")
        
        # 特殊处理"中国先进技术"这个实体
        if "中国先进技术" in ques:
            dom_.append("中国先进技术")
            ques = ques.replace("中国先进技术", "")
            
        for wl in ques_word_list:
            self.match_word(wl, li_aut, aut_)
            self.match_word(wl, li_jou, jou_)
            self.match_word(wl, li_key, key_)
            self.match_word(wl, li_ins, ins_)
            self.match_word(wl, li_dom, dom_)
            
        # 如果问题中包含"写了"、"撰写"等动词但未识别到作者，尝试从问题中提取
        if not aut_ and any(word in ques for word in ['写了', '撰写', '写作']):
            # 尝试提取作者名（假设作者名在动词前）
            for i, word in enumerate(ques_word_list):
                if word in ['写了', '撰写', '写作'] and i > 0:
                    potential_author = ques_word_list[i-1]
                    if potential_author in li_aut:
                        aut_.append(potential_author)
            
        enti_dicts['Article'] = ques_article
        enti_dicts['Author'] = aut_
        enti_dicts['Journal'] = jou_
        enti_dicts['Keyword'] = key_
        enti_dicts['Institution'] = ins_
        enti_dicts['TechnologyDomain'] = dom_
        
        return enti_dicts, ques
    
    def art_match(self, li_art, en_art):#找出输入正确的文章名及相似文章名
        simi = []
        right_name = []
        for ea in en_art:
            for la in li_art:
                if ea in la and ea != la:
                    simi.append(la)
                if ea == la:
                    right_name.append(la)
        return simi, right_name
    
    def match_word(self, word, li, li_):#判断实体是否出现在问题中
        for l in li:
            if word == l:
                li_.append(l)

        