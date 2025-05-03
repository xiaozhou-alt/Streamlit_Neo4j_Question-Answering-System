import os
import streamlit as st
from streamlit_chatbox import ChatBox, Markdown
import time
from question import question_from_user
from answer import answer_from_robot
from streamlit_agraph import agraph, Config
from match import match_things
from st_aggrid import AgGrid, GridOptionsBuilder
from py2neo import Graph

def kg_graph(nodes, edges):
    config = Config(
        width=800,
        height=600,
        directed=True,
        physics=True,
        hierarchical=False,
        nodeHighlightBehavior=True,
        highlightColor="#F7A7A6",
        collapsible=True
    )
    return agraph(nodes=nodes, edges=edges, config=config)

chat_box = ChatBox(
    assistant_avatar="./imgs/robot.png",
    user_avatar="./imgs/user.png",
    greetings=[
        "# 🌟 欢迎使用学术论文知识图谱问答系统 🌟",
        "### 🤖 我是一个基于学术论文知识图谱的智能问答机器人，主要功能包括：",
        "### 🔍 学术论文知识图谱问答 📊 相关知识点可视化展示",
        "### 📚 知识库包含：",
        "- 学术论文信息（标题、摘要、关键词等）",
        "- 作者及机构信息", 
        "- 期刊/会议信息（ISSN、发表论文等）",
        "- 技术领域分类信息",
        "### 💡 您可以这样提问：",
        "### 1. 论文信息查询",
        "   • 介绍一下《XXX》这篇论文",
        "   • 《XXX》属于哪个领域",
        "### 2. 作者信息查询", 
        "   • 作者XXX撰写了哪些论文",
        "   • 作者XXX隶属于哪个单位",
        "### 3. 关键词查询",
        "   • 关键词XXX相关的论文有哪些",
        "### 4. 机构查询",
        "   • 机构XXX包含哪些作者",
        "### 5. 期刊查询",
        "   • 期刊XXX的ISSN编号是什么",
        "   • 期刊XXX发表了哪些论文",
        "### 6. 查询",
        "   • 中国先进技术包含哪几个方面",
        "## ⚠️ 注意事项",
        "- 查询论文时请使用《书名号》括起论文标题",
        "- 期刊名称需完整，如包含括号内容",
        "- 系统支持中英文混合查询",
        "- 结果按相关性排序"]
        )

with st.sidebar:
    st.header('学术论文知识图谱问答系统')
    tab1, tab2 = st.tabs(["模糊搜索","知识图谱"])
    with tab1:
        col1, col2 = st.columns([1, 3])
        with col1:
            option = st.selectbox('搜索内容', ['论文', '作者', '期刊', '关键词'], index=0)
        with col2:
            name = st.text_input('请在此输入名称: ', key='search_input')
        col3, col4 = st.columns(2)
        with col3:
            num = st.number_input(label='查询数量', min_value=1, max_value=20, value=5, step=1)
        with col4:
            rate = st.number_input(label='相似度', min_value=0.0, max_value=1.0, value=0.6, step=0.1)
        
        if st.button('搜索', key='search_button') and name.strip():
            try:
                with st.spinner('正在搜索...'):
                    df = match_things(name, option, num, rate)
                    if not df.empty:
                        gb = GridOptionsBuilder.from_dataframe(df)
                        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=10)
                        gb.configure_default_column(width=200)
                        go = gb.build()
                        AgGrid(df, 
                              gridOptions=go, 
                              height=min(400, 35*(len(df)+1)), 
                              fit_columns_on_grid_load=True,
                              reload_data=False,
                              theme='streamlit')
                    else:
                        st.warning("未找到匹配结果")
            except Exception as e:
                st.error(f"搜索出错: {str(e)}")
                st.stop()


chat_box.init_session()
chat_box.output_messages()

if query := st.chat_input('请输入您想问的问题……'):
    chat_box.user_say(query)
    ques = question_from_user(query)
    
    # 检查问题是否有效
    if not ques.IR or not any(ques.EN.values()):
        chat_box.ai_say(
            [
                Markdown("""
                ⚠️ 查询出错：
                - 未识别到有效问题意图
                - 或未找到相关实体信息
                
                请尝试以下方式提问：
                1. 使用《书名号》括起论文标题
                2. 确保期刊名称完整(包含括号内容)
                3. 使用更明确的关键词或名称
                """, in_expander=False, expanded=True, title="回答")
            ]
        )
    else:
        anwser = answer_from_robot(ques.IR, ques.EN, ques.right_art, ques.li_art)
        
        # 检查是否找到任何实体信息
        if not any([ques.right_art, ques.li_art, anwser.answer_list]):
            entity_type = "论文" if "《" in query else "作者/机构/期刊"
            chat_box.ai_say(
                [
                    Markdown(f"""
                    ⚠️ 未找到{entity_type}的相关信息
                    
                    可能原因：
                    1. 名称输入有误
                    2. 数据库中暂无此{entity_type}信息
                    3. 相似度阈值设置过高
                    
                    建议：
                    1. 检查名称拼写
                    2. 尝试降低相似度阈值
                    3. 使用模糊搜索功能查询
                    """, in_expander=False, expanded=True, title="回答")
                ]
            )
        else:
            # 原有回答处理代码
            elements = chat_box.ai_say(
                [
                    Markdown("正在思考。。。", in_expander=False,
                             expanded=True, title="answer"),
                ]
            )
            
            # 确保answer_list不为空
            if not hasattr(anwser, 'answer_list') or not anwser.answer_list:
                anwser.answer_list = ["未能获取到回答信息"]
            
            # 构建回答文本
            text = "<div style='line-height:1.6;'>"
            for x in anwser.answer_list:
                if x.startswith("## "):
                    text += f"<h3 style='margin-top:1em;'>{x[3:]}</h3>"
                elif x.startswith("- "):
                    text += f"<p style='margin-left:1em; margin-bottom:0.5em;'>{x}</p>"
                elif x.startswith("  摘要:"):
                    text += f"<p style='margin-left:2em; color:#666; font-size:0.9em;'>{x}</p>"
                elif ":" in x and not x.startswith("http"):  # 处理键值对格式
                    key, value = x.split(":", 1)
                    text += f"<p><strong>{key}:</strong> {value.strip()}</p>"
                else:
                    text += f"<p>{x}</p>"
            text += "</div>"
            for x in anwser.answer_list:
                if x.startswith("## "):
                    text += f"## {x[3:]}\n\n"
                elif x.startswith("**"):
                    text += f"**{x[2:-2]}**\n\n"
                else:
                    text += f"{x}\n\n"
            
            # 直接使用Markdown显示回答
            chat_box.update_msg(
                Markdown(text, in_expander=False, expanded=True, title="回答"),
                element_index=0,
                streaming=False,
                state="complete"
            )
            
            # 显示知识图谱
            with st.sidebar:
                with tab2:
                    if anwser.all_nodes and anwser.all_edges:
                        # 调整图谱配置使布局更清晰
                        config = Config(
                            width=800,
                            height=600,
                            directed=True,
                            physics=True,
                            hierarchical=False,
                            nodeHighlightBehavior=True,
                            highlightColor="#F7A7A6",
                            collapsible=True,
                            link={'highlightColor': '#8A2BE2'}
                        )
                        agraph(nodes=anwser.all_nodes, edges=anwser.all_edges, config=config)
                    else:
                        st.warning("未找到相关图谱信息")
                        # 添加CSS样式使toast居中
                        st.markdown("""
                        <style>
                            .toast-container {
                                position: fixed;
                                top: 50%;
                                left: 50%;
                                transform: translate(-50%, -50%);
                                z-index: 9999;
                            }
                        </style>
                        """, unsafe_allow_html=True)
                        st.toast("⚠️ 未查询到有效内容")
        time.sleep(1)
        if anwser.prob_mov:
            aps = ''
            for ap in anwser.prob_mov:
                aps += ap+'<br>'
            chat_box.ai_say(
            [
                Markdown(aps, in_expander=True,
                         title="您可能要找的是：",state='complete'),
            ]
            )
        time.sleep(1)
        if anwser.simi_mov:
            sms = ''
            for sm in anwser.simi_mov:
                sms += sm+'<br>'
            chat_box.ai_say(
            [
                Markdown(sms, in_expander=True,
                       title="相关推荐：",state='complete'),
            ]
            )


def main():
    # 确保静态文件路径正确
    if not os.path.exists('./imgs'):
        os.makedirs('./imgs')
    
    # 测试Neo4j连接
    try:
        test_graph = Graph("bolt://localhost:7687", auth=("neo4j", "zhj20031218"))
        test_graph.run("MATCH (n) RETURN n LIMIT 1")
        st.success("Neo4j连接成功！")
    except Exception as e:
        st.error(f"Neo4j连接失败: {str(e)}")


if __name__ == '__main__':
    # 修改为明确绑定到0.0.0.0
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--server.address', default='0.0.0.0')
    parser.add_argument('--server.port', type=int, default=8501)
    args, _ = parser.parse_known_args()
    
    # 启动服务
    main()