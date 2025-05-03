from py2neo import Graph
from streamlit_agraph import agraph, Node, Edge, Config
import difflib

# 知识图谱连接参数
uri = "bolt://localhost:7687"
username = "neo4j"
password = "zhj20031218"

class answer_from_robot():
    def __init__(self, IR, en_dict, right_name, art_li):
        self.graph = Graph(uri, auth=(username,password))
        self.IR = IR
        self.en_dict = en_dict
        self.right_name = right_name
        self.art_li = art_li
        self.prob_mov = []
        self.simi_mov = []
        
        # 确保answer_ques方法被调用
        self.answer_list, self.all_nodes, self.all_edges = self.answer_ques(self.IR, self.en_dict, self.right_name)
        if not self.answer_list:
            self.answer_list = ["未能找到相关信息，请尝试其他问题"]
    
    def answer_ques(self, IR, en_dict, right_name):
        relation_ques = ['AFFILIATED_WITH', 'BELONGS_TO', 'HAS_KEYWORD', 
                        'PUBLISHED_IN', 'SUB_DOMAIN_OF', 'WRITTEN_BY']
        property_ques = ['abstract', 'isbn_issn', 'notes', 'title', 'url']
        node = []
        edge = []
        all_nodes = []
        all_edges = []
        all_answers = []
        
        if not IR:
            all_answers.append('未识别到有效问题')
        
        # 增加意图识别调试信息
        debug_info = f"识别到的意图: {IR}, 实体: {en_dict}"
        print(debug_info)  # 调试用
        
        for ir in IR:
            # 增加意图检查
            if ir == 'PUBLISHED_IN':
                if not en_dict.get('Journal') and not en_dict.get('Article'):
                    all_answers.append("未识别到期刊或文章信息")
                    continue
                    
            if ir in relation_ques:
                answers, nodes, edges, node, edge = self.relation_answers(en_dict, right_name, ir, node, edge)
                all_answers.extend(answers)
                all_nodes.extend(nodes)
                all_edges.extend(edges)
                
            if ir in property_ques:
                answers, nodes, edges, node = self.property_answers(en_dict, right_name, ir, node)
                all_answers.extend(answers)
                all_nodes.extend(nodes)
                all_edges.extend(edges)

            if ir == '介绍':
                answers, nodes, edges, node = self.intro_article(en_dict, right_name, node)
                all_answers.extend(answers)
                all_nodes.extend(nodes)
                all_edges.extend(edges)
                
        return all_answers, all_nodes, all_edges

    def relation_answers(self, en_dict, right_name, relation, node, edge):
        nodes = []
        edges = []
        answers = []
        
        if relation == 'WRITTEN_BY':
            # 处理作者查询文章的情况
            if en_dict['Author']:
                for author in en_dict['Author']:
                    answer = self.graph.run(f"MATCH (a:Author {{name:'{author}'}})-[:WRITTEN_BY]->(p:Article) RETURN p").data()
                    if author not in node:
                        nodes.append(Node(id=author, label=author, size=25, color='blue'))
                        node.append(author)
                    if not answer:
                        answers.append(f"没有找到{author}撰写的论文")
                    else:
                        article_titles = []
                        for an in answer:
                            if 'p' in an and an['p']:
                                article_title = an['p'].get('title', '未知文章')
                                article_titles.append(article_title)
                                if article_title not in node:
                                    nodes.append(Node(id=article_title, label=article_title, size=25, color='green'))
                                    node.append(article_title)
                                if (author, article_title) not in edge:
                                    edges.append(Edge(source=author, label=relation, target=article_title))
                                    edge.append((author, article_title))
                        if article_titles:
                            answers.append(f"{author}撰写的论文有:")
                            answers.extend([f"- {title}" for title in article_titles])
            
            # 处理文章查询作者的情况
            if en_dict['Article']:
                for art in en_dict['Article']:
                    if art in right_name:
                        answer = self.graph.run(f"MATCH (a:Article {{title:'{art}'}})<-[:WRITTEN_BY]-(p:Author) RETURN p").data()
                        if art not in node:
                            nodes.append(Node(id=art, label=art, size=25, color='green'))
                            node.append(art)
                        if not answer:
                            answers.append(f"《{art}》的作者信息暂缺")
                        else:
                            author_names = []
                            for an in answer:
                                if 'p' in an and an['p']:
                                    author_name = an['p'].get('name', '未知作者')
                                    author_names.append(author_name)
                                    if author_name not in node:
                                        nodes.append(Node(id=author_name, label=author_name, size=25, color='blue'))
                                        node.append(author_name)
                                    if (art, author_name) not in edge:
                                        edges.append(Edge(source=art, label=relation, target=author_name))
                                        edge.append((art, author_name))
                            if author_names:
                                answers.append(f"《{art}》的作者是: {', '.join(author_names)}")
        
        elif relation == 'PUBLISHED_IN':
            # 处理文章查询期刊的情况
            if en_dict['Article']:
                for art in en_dict['Article']:
                    if art in right_name:
                        answer = self.graph.run(f"MATCH (a:Article {{title:'{art}'}})-[:PUBLISHED_IN]->(p:Journal) RETURN p").data()
                        if art not in node:
                            nodes.append(Node(id=art, label=art, size=25, color='green'))
                            node.append(art)
                        if not answer:
                            answers.append(f"《{art}》的发表期刊信息暂缺")
                        else:
                            journal_names = []
                            for an in answer:
                                if 'p' in an and an['p']:  # 确保结果中有p字段且不为空
                                    journal_name = an['p'].get('name', '未知期刊')
                                    if journal_name:  # 确保期刊名称不为空
                                        journal_names.append(journal_name)
                                        if journal_name not in node:
                                            nodes.append(Node(id=journal_name, label=journal_name, size=25, color='orange'))
                                            node.append(journal_name)
                                        if (art, journal_name) not in edge:
                                            edges.append(Edge(source=art, label=relation, target=journal_name))
                                            edge.append((art, journal_name))
                            if journal_names:  # 确保有期刊信息才显示
                                answers.append(f"《{art}》发表在: {', '.join(journal_names)}")
                            else:
                                answers.append(f"《{art}》的发表期刊信息暂缺")
            
            # 增强期刊查询文章的逻辑
            if en_dict['Journal']:
                for journal in en_dict['Journal']:
                    # 先检查期刊是否存在
                    journal_exists = self.graph.run(f"MATCH (j:Journal) WHERE j.name CONTAINS '{journal}' RETURN j").data()
                    if not journal_exists:
                        answers.append(f"未找到期刊《{journal}》的信息")
                        continue
                        
                    # 查询该期刊发表的文章
                    answer = self.graph.run(f"""
                        MATCH (a:Article)-[:PUBLISHED_IN]->(j:Journal)
                        WHERE j.name CONTAINS '{journal}'
                        RETURN a.title as title
                        ORDER BY a.title
                        LIMIT 10
                    """).data()
                    
                    # 获取期刊全名
                    journal_fullname = journal_exists[0]['j']['name'] if journal_exists else journal
                    
                    # 添加期刊节点
                    if journal_fullname not in node:
                        nodes.append(Node(id=journal_fullname, label=journal_fullname, size=30, color='orange'))
                        node.append(journal_fullname)
                    
                    if not answer:
                        answers.append(f"期刊《{journal_fullname}》目前没有发表文章记录")
                    else:
                        article_titles = [art['title'] for art in answer]
                        answers.append(f"## 期刊《{journal_fullname}》发表的文章:")
                        answers.extend([f"- {title}" for title in article_titles])
                        
                        # 添加文章节点和边
                        for title in article_titles:
                            if title not in node:
                                nodes.append(Node(id=title, label=title, size=25, color='green'))
                                node.append(title)
                            if (title, journal_fullname) not in edge:
                                edges.append(Edge(source=title, label=relation, target=journal_fullname))
                                edge.append((title, journal_fullname))

        elif relation == 'BELONGS_TO':
            if en_dict['Article']:
                for art in en_dict['Article']:
                    if art in right_name:
                        # 修改查询语句，确保正确获取技术领域
                        answer = self.graph.run(f"""
                            MATCH (a:Article {{title:'{art}'}})-[:BELONGS_TO]->(td:TechnologyDomain)
                            RETURN td.name as domain_name
                            ORDER BY td.name
                        """).data()
                        
                        if art not in node:
                            nodes.append(Node(id=art, label=art, size=25, color='green'))
                            node.append(art)
                            
                        if not answer:
                            answers.append(f"《{art}》的技术领域分类信息暂缺")
                        else:
                            domains = [item['domain_name'] for item in answer]
                            answers.append(f"《{art}》属于以下技术领域:")
                            answers.extend([f"- {domain}" for domain in domains])
                            
                            # 添加节点和边
                            for domain in domains:
                                if domain not in node:
                                    nodes.append(Node(id=domain, label=domain, size=25, color='purple'))
                                    node.append(domain)
                                if (art, domain) not in edge:
                                    edges.append(Edge(source=art, label=relation, target=domain))
                                    edge.append((art, domain))
                            
                            answers.append(f"《{art}》属于以下技术领域:")
                            answers.extend([f"- {domain}" for domain in domains])

        elif relation == 'HAS_KEYWORD':
            if en_dict['Article']:
                for art in en_dict['Article']:
                    if art in right_name:
                        answer = self.graph.run(f"MATCH (a:Article {{title:'{art}'}})-[:HAS_KEYWORD]->(p:Keyword) RETURN p").data()
                        if art not in node:
                            nodes.append(Node(id=art, label=art, size=25, color='green'))
                            node.append(art)
                        if not answer:
                            answers.append(f"《{art}》的关键词信息暂缺")
                        else:
                            keyword_names = []
                            for an in answer:
                                keyword_name = an['p']['name']
                                keyword_names.append(keyword_name)
                                if keyword_name not in node:
                                    nodes.append(Node(id=keyword_name, label=keyword_name, size=25, color='red'))
                                    node.append(keyword_name)
                                if (art, keyword_name) not in edge:
                                    edges.append(Edge(source=art, label=relation, target=keyword_name))
                                    edge.append((art, keyword_name))
                            answers.append(f"《{art}》的关键词有: {', '.join(keyword_names)}")
        
        # elif relation == 'HAS_KEYWORD':
            if en_dict['Keyword']:
                for keyword in en_dict['Keyword']:
                    answer = self.graph.run(f"""
                        MATCH (k:Keyword {{keyword:'{keyword}'}})<-[:HAS_KEYWORD]-(a:Article)
                        RETURN a.title as title
                        ORDER BY a.title
                        LIMIT 10
                    """).data()
                    
                    if not answer:
                        answers.append(f"没有找到与关键词'{keyword}'相关的论文")
                    else:
                        article_titles = [art['title'] for art in answer]
                        answers.append(f"## 关键词'{keyword}'相关论文")
                        answers.extend([f"- {title}" for title in article_titles])
                        
                        # 更新知识图谱节点和边
                        if keyword not in node:
                            nodes.append(Node(id=keyword, label=keyword, size=25, color='red'))
                            node.append(keyword)
                            
                        for title in article_titles:
                            if title not in node:
                                nodes.append(Node(id=title, label=title, size=25, color='green'))
                                node.append(title)
                            if (title, keyword) not in edge:
                                edges.append(Edge(source=title, label=relation, target=keyword))
                                edge.append((title, keyword))
        
        elif relation == 'SUB_DOMAIN_OF':
            if en_dict.get('TechnologyDomain'):
                # 固定查询"中国先进技术"的子领域
                answer = self.graph.run("""
                    MATCH (d:TechnologyDomain)-[:SUB_DOMAIN_OF]->(p:AdvancedTechnologyInChina {name:'中国先进技术'})
                    RETURN d.name as name
                    ORDER BY d.name
                """).data()
                
                # 确保"中国先进技术"节点存在
                if '中国先进技术' not in node:
                    nodes.append(Node(id='中国先进技术', label='中国先进技术', size=30, color='yellow'))
                    node.append('中国先进技术')
                
                if not answer:
                    answers.append("'中国先进技术'的分类信息暂缺")
                else:
                    tech_names = [tech['name'] for tech in answer if tech.get('name')]
                    if tech_names:
                        answers.append("## '中国先进技术'包含以下技术领域:")
                        answers.extend([f"- {name}" for name in tech_names])
                        
                        for tech_name in tech_names:
                            if tech_name not in node:
                                nodes.append(Node(id=tech_name, label=tech_name, size=25, color='purple'))
                                node.append(tech_name)
                            if (tech_name, '中国先进技术') not in edge:
                                edges.append(Edge(source=tech_name, label=relation, target='中国先进技术'))
                                edge.append((tech_name, '中国先进技术'))

        elif relation == 'AFFILIATED_WITH':
            # 处理作者查询机构的情况
            if en_dict['Author']:
                for author in en_dict['Author']:
                    answer = self.graph.run(f"MATCH (a:Author {{name:'{author}'}})-[:AFFILIATED_WITH]->(i:Institution) RETURN i").data()
                    if author not in node:
                        nodes.append(Node(id=author, label=author, size=25, color='blue'))
                        node.append(author)
                    if not answer:
                        answers.append(f"没有找到{author}的所属机构信息")
                    else:
                        institutions = []
                        for an in answer:
                            if 'i' in an and an['i']:
                                institution = an['i'].get('address', '未知机构')
                                if institution:
                                    institutions.append(institution)
                                    if institution not in node:
                                        nodes.append(Node(id=institution, label=institution, size=25, color='gray'))
                                        node.append(institution)
                                    if (author, institution) not in edge:
                                        edges.append(Edge(source=author, label=relation, target=institution))
                                        edge.append((author, institution))
                        if institutions:
                            answers.append(f"{author}隶属于以下单位:")
                            answers.extend([f"- {inst}" for inst in institutions])
            
            # 处理机构查询作者的情况
            if en_dict['Institution']:
                for institution in en_dict['Institution']:
                    answer = self.graph.run(f"MATCH (a:Author)-[:AFFILIATED_WITH]->(i:Institution {{address:'{institution}'}}) RETURN a").data()
                    if institution not in node:
                        nodes.append(Node(id=institution, label=institution, size=25, color='gray'))
                        node.append(institution)
                    if not answer:
                        answers.append(f"机构{institution}的作者信息暂缺")
                    else:
                        author_names = []
                        for an in answer:
                            if 'a' in an and an['a']:
                                author_name = an['a'].get('name', '未知作者')
                                if author_name:
                                    author_names.append(author_name)
                                    if author_name not in node:
                                        nodes.append(Node(id=author_name, label=author_name, size=25, color='blue'))
                                        node.append(author_name)
                                    if (author_name, institution) not in edge:
                                        edges.append(Edge(source=author_name, label=relation, target=institution))
                                        edge.append((author_name, institution))
                        if author_names:
                            answers.append(f"机构{institution}包含以下作者:")
                            answers.extend([f"- {name}" for name in author_names])

        return answers, nodes, edges, node, edge

    def property_answers(self, en_dict, right_name, property_name, node):
        nodes = []
        edges = []
        answers = []
        
        if en_dict['Article']:
            for art in en_dict['Article']:
                if art in right_name:
                    answer = self.graph.run(f"MATCH (a:Article {{title:'{art}'}}) RETURN a.{property_name}").data()
                    if art not in node:
                        nodes.append(Node(id=art, label=art, size=25, color='green'))
                        node.append(art)
                    if not answer or answer[0][f'a.{property_name}'] is None:
                        answers.append(f"《{art}》的{property_name}信息暂缺")
                    else:
                        value = answer[0][f'a.{property_name}']
                        answers.append(f"《{art}》的{property_name}是: {value}")
        
        # 增强期刊查询逻辑
        if property_name == 'isbn_issn' and en_dict.get('Journal'):
            for journal in en_dict['Journal']:
                # 查询期刊的ISSN和其他属性
                answer = self.graph.run(f"""
                    MATCH (j:Journal {{name:'{journal}'}}) 
                    RETURN j.issn as issn
                """).data()
                
                if not answer:
                    answers.append(f"未找到期刊《{journal}》的信息")
                    continue
                    
                journal_data = answer[0]
                issn = journal_data.get('issn')
                full_name = journal_data.get('name', journal)
                
                # 添加期刊节点
                if full_name not in node:
                    nodes.append(Node(id=full_name, label=full_name, size=30, color='orange'))
                    node.append(full_name)
                
                if not issn:
                    answers.append(f"期刊《{full_name}》的ISSN编号信息暂缺")
                else:
                    answers.append(f"期刊《{full_name}》的ISSN编号是: {issn}")

        return answers, nodes, edges, node

    def get_node_color(self, label_type):
        color_map = {
            'Article': 'green',
            'Author': 'blue',
            'Journal': 'orange',
            'Keyword': 'red',
            'Institution': 'gray',
            'TechnologyDomain': 'purple'
        }
        return color_map.get(label_type, '#F7A7A6')  # 默认颜色

    def intro_article(self, en_dict, right_name, node):
        nodes = []
        edges = []
        answers = []
        
        if en_dict['Article']:
            for art in en_dict['Article']:
                if art in right_name:
                    # 查询文章基本信息
                    article_info = self.graph.run(f"MATCH (a:Article {{title:'{art}'}}) RETURN a").data()
                    
                    if art not in node:
                        nodes.append(Node(id=art, label=art, size=25, color='green'))
                        node.append(art)
                    
                    if not article_info:
                        answers.append(f"《{art}》的基本信息暂缺")
                    else:
                        # 添加文章基本信息到回答
                        info = article_info[0]['a']
                        answers.append(f"文章《{art}》详细信息")
                        answers.append(f"标题: {info.get('title', '无')}")
                        answers.append(f"摘要: {info.get('abstract', '无')}")
                        answers.append(f"ISSN/ISBN: {info.get('isbn_issn', '无')}")
                        answers.append(f"URL: {info.get('url', '无')}")
                        answers.append(f"Notes: {info.get('notes', '无')}")
                        
                        # 获取关键词信息
                        keyword_query = f"""
                        MATCH (a:Article {{title:'{art}'}})-[:HAS_KEYWORD]->(k:Keyword)
                        RETURN k.keyword as keyword
                        """
                        keyword_results = self.graph.run(keyword_query).data()
                        if keyword_results:
                            keywords = [kw['keyword'] for kw in keyword_results if kw['keyword']]
                            answers.append(f"关键词: {', '.join(keywords)}")
                        
                        # 获取其他关系信息
                        relations = ['WRITTEN_BY', 'PUBLISHED_IN', 'BELONGS_TO','HAS_KEYWORD']
                        for rel in relations:
                            if rel == 'WRITTEN_BY':
                                # 作者指向论文的关系
                                results = self.graph.run(f"MATCH (a:Article {{title:'{art}'}})<-[:{rel}]-(n) RETURN n").data()
                            else:
                                # 其他关系保持原方向
                                results = self.graph.run(f"MATCH (a:Article {{title:'{art}'}})-[:{rel}]->(n) RETURN n").data()
                            
                            if results:
                                related_items = []
                                for r in results:
                                    if r['n']:
                                        name = r['n'].get('name') or r['n'].get('title') or r['n'].get('keyword')
                                        if name:
                                            related_items.append(name)
                                            if name not in node:
                                                nodes.append(Node(id=name, label=name, size=25, 
                                                               color=self.get_node_color(list(r['n'].labels)[0])))
                                                node.append(name)
                                            edges.append(Edge(source=art if rel != 'WRITTEN_BY' else name, 
                                                           label=rel, 
                                                           target=name if rel != 'WRITTEN_BY' else art))
                                if related_items:
                                    answers.append(f"{rel.replace('_', ' ')}: {', '.join(related_items)}")
        
        return answers, nodes, edges, node
