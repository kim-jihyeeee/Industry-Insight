import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import datetime, requests, re
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. 페이지 설정
st.set_page_config(page_title="AE Total Tool v13.1", layout="wide")

# 🌟 Gemini API 설정 (안정적 경로 고정)
API_KEY = "AQ.Ab8RN6Lc9LYyyyi-oE7eVOZfjfe8AKJIQ8u3SnPmUce-LjoZRw"

@st.cache_resource
def init_ai():
    if not API_KEY: return None
    try:
        genai.configure(api_key=API_KEY)
        return genai.GenerativeModel('models/gemini-1.5-flash-latest')
    except: return None

ai_engine = init_ai()

@st.cache_data
def load_font():
    try:
        url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Bold.ttf"
        res = requests.get(url)
        with open("nanum_font.ttf", "wb") as f: f.write(res.content)
        return "nanum_font.ttf"
    except: return None

FONT_PATH = load_font()

# 세션 데이터 초기화
if 'history_db' not in st.session_state: 
    st.session_state.history_db = pd.DataFrame(columns=['날짜', '광고주명', '소통내용'])

# UI 스타일
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; background-color: #FFB300; color: white; font-weight: bold; height: 3em; }
    .issue-tag { display: inline-block; padding: 10px 20px; margin: 5px; background-color: #fff; border: 1px solid #ddd; border-radius: 5px; font-weight: bold; }
    .section-header { font-size: 1.3em; font-weight: bold; margin: 20px 0; border-bottom: 2px solid #FFB300; padding-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

# 시각화 함수
def create_wc(text):
    if not text or not text.strip(): return None
    wc = WordCloud(font_path=FONT_PATH, width=1200, height=600, background_color='white', colormap='tab10').generate(text)
    fig, ax = plt.subplots(figsize=(15, 7))
    ax.imshow(wc, interpolation='bilinear'); ax.axis('off')
    return fig

# --- 사이드바 메뉴 (화면 섞임 방지를 위해 radio로 통합) ---
with st.sidebar:
    st.title("🚀 AE Total Tool v13.1")
    st.markdown("### 📂 메뉴 선택")
    # 🌟 모든 메뉴를 하나의 선택지로 묶어 화면 중복 노출 차단
    main_menu = st.radio("항목을 선택하세요", 
                         ["🌐 AI Trend Radar", "📂 광고주 DB 관리", "📝 관리 이력 입력", "📊 디지털 리포트(내부)"])

# 1. AI Trend Radar
if main_menu == "🌐 AI Trend Radar":
    st.title("🌐 AI Trend Radar v13.1")
    t1, t2 = st.tabs(["📰 뉴스 AI 분석", "🔍 검색 AI 분석"])
    
    with t1:
        c1, c2 = st.columns([3, 1])
        n_keyword = c1.text_input("분석 키워드", placeholder="예: 도라지배즙")
        n_period = c2.selectbox("기간", ["3일", "7일", "30일", "60일"], index=2)
        
        if st.button("🚀 뉴스 분석 시작"):
            with st.spinner("데이터 분석 중..."):
                rss = f"https://news.google.com/rss/search?q={n_keyword}&hl=ko&gl=KR&ceid=KR:ko"
                try:
                    res = requests.get(rss, timeout=10)
                    titles = [re.split(r' - | \| ', i.title.get_text())[0] for i in BeautifulSoup(res.text, 'xml').find_all('item')[:15]]
                    if titles:
                        # 태그 추출
                        tags = re.findall(r'#\w+', ai_engine.generate_content(f"{titles}에서 핵심 이슈 5개만 #단어 형태로 뽑아줘").text)
                        st.markdown("<div class='section-header'>📌 주요 이슈 키워드</div>", unsafe_allow_html=True)
                        st.markdown("".join([f"<span class='issue-tag'>{t}</span>" for t in tags[:5]]), unsafe_allow_html=True)
                        st.pyplot(create_wc(" ".join(titles)))
                    else: st.warning("데이터가 없습니다.")
                except: st.error("통신 오류가 발생했습니다. 다시 시도해 주세요.")

    with t2:
        s_keyword = st.text_input("검색 트렌드 키워드", placeholder="예: 환절기 건강 관리")
        if st.button("🔍 검색 분석 시작"):
            rss = f"https://news.google.com/rss/search?q={s_keyword}+추천+트렌드&hl=ko&gl=KR&ceid=KR:ko"
            titles = [i.title.get_text() for i in BeautifulSoup(requests.get(rss).text, 'xml').find_all('item')[:15]]
            if titles:
                st.pyplot(create_wc(" ".join(titles)))

# 2. 광고주 DB 관리
elif main_menu == "📂 광고주 DB 관리":
    st.header("📂 광고주 DB 관리")
    up_f = st.file_uploader("💾 백업 파일(XLSX) 업로드", type=['xlsx'])
    if up_f:
        st.session_state.history_db = pd.read_excel(up_f, engine='openpyxl')
        st.success("데이터 로드 완료!")
    st.dataframe(st.session_state.history_db, use_container_width=True)

# 3. 관리 이력 입력
elif main_menu == "📝 관리 이력 입력":
    st.header("📝 관리 이력 입력")
    client_list = sorted(st.session_state.history_db['광고주명'].dropna().unique().tolist())
    
    with st.form("input_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        in_date = col1.date_input("날짜", datetime.date.today())
        # 🌟 광고주 검색/선택 기능 적용
        in_name = col2.selectbox("광고주 검색/선택", ["직접 입력"] + client_list)
        if in_name == "직접 입력":
            in_name = st.text_input("새 광고주명 입력")
            
        in_content = st.text_area("소통 내용")
        if st.form_submit_button("💾 데이터 저장"):
            if in_name and in_content:
                new_row = pd.DataFrame({'날짜': [pd.to_datetime(in_date)], '광고주명': [in_name], '소통내용': [in_content]})
                st.session_state.history_db = pd.concat([st.session_state.history_db, new_row], ignore_index=True)
                st.success("저장되었습니다.")

# 4. 디지털 리포트(내부)
elif main_menu == "📊 디지털 리포트(내부)":
    st.header("📊 내부 소통 이슈 리포트")
    if not st.session_state.history_db.empty:
        client_list = sorted(st.session_state.history_db['광고주명'].dropna().unique().tolist())
        c1, c2 = st.columns(2)
        # 🌟 광고주 검색/선택 기능 적용
        target = c1.selectbox("분석할 광고주 선택", client_list)
        
        # 🌟 기간 설정 필터 추가
        st.session_state.history_db['날짜'] = pd.to_datetime(st.session_state.history_db['날짜'])
        min_date = st.session_state.history_db['날짜'].min().date()
        date_range = c2.date_input("분석 기간", [min_date, datetime.date.today()])
        
        f_df = st.session_state.history_db[st.session_state.history_db['광고주명'] == target]
        if len(date_range) == 2:
            f_df = f_df[(f_df['날짜'].dt.date >= date_range[0]) & (f_df['날짜'].dt.date <= date_range[1])]
            
        if not f_df.empty:
            st.markdown(f"### 🎯 {target} 주요 이슈 마인드맵")
            st.pyplot(create_wc(" ".join(f_df['소통내용'].astype(str))))
        else: st.warning("해당 기간에 소통 데이터가 없습니다.")
    else: st.info("DB에 데이터가 없습니다.")
