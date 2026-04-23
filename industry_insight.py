import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import datetime, requests, re
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. 페이지 설정
st.set_page_config(page_title="AE Total Tool v13.4", layout="wide")

# 🌟 Gemini API 설정 (경로 안정화)
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

# 🌟 네이버 데이터랩 기준 표준 카테고리
NAVER_CATEGORIES = ["패션의류", "패션잡화", "화장품/미용", "디지털/가전", "가구/인테리어", "출산/육아", "식품", "스포츠/레저", "생활/건강", "여가/생활편의", "면세점", "도서"]

# 세션 데이터 초기화
if 'history_db' not in st.session_state: 
    st.session_state.history_db = pd.DataFrame(columns=['날짜', '광고주명', '소통내용', '카테고리'])

# UI 스타일 설정
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; background-color: #FFB300; color: white; font-weight: bold; height: 3em; }
    .issue-tag { display: inline-block; padding: 10px 20px; margin: 5px; background-color: #fff; border: 1px solid #FFB300; border-radius: 5px; font-weight: bold; color: #FFB300; }
    .section-header { font-size: 1.4em; font-weight: bold; margin: 30px 0 10px 0; border-left: 6px solid #FFB300; padding-left: 12px; color: #333; }
    </style>
""", unsafe_allow_html=True)

# 시각화 함수 (가독성 위해 높이 조절 가능)
def create_wc(text, height=600):
    if not text or not text.strip(): return None
    wc = WordCloud(font_path=FONT_PATH, width=1200, height=height, background_color='white', colormap='tab10').generate(text)
    fig, ax = plt.subplots(figsize=(15, height/100))
    ax.imshow(wc, interpolation='bilinear'); ax.axis('off')
    return fig

# --- 사이드바 메뉴 ---
with st.sidebar:
    st.title("🚀 AE Total Tool v13.4")
    main_menu = st.radio("메뉴 선택", ["🌐 AI Trend Radar", "📂 광고주 DB 관리", "📝 관리 이력 입력", "📊 내부 소통 이슈 리포트"])

# 1. AI Trend Radar
if main_menu == "🌐 AI Trend Radar":
    st.title("🌐 AI Trend Radar")
    t1, t2 = st.tabs(["📰 뉴스 AI 분석", "🔍 검색 AI 분석"])
    
    with t1:
        c1, c2 = st.columns([3, 1])
        n_keyword = c1.text_input("뉴스 분석 키워드", placeholder="예: 콘드로이친", key="n_k")
        n_period = c2.selectbox("기간 설정", ["3일", "7일", "한달", "60일", "분기"], index=2, key="n_p")
        
        if st.button("🚀 뉴스 AI 분석 시작"):
            with st.spinner("최신 이슈 분석 중..."):
                rss = f"https://news.google.com/rss/search?q={n_keyword}&hl=ko&gl=KR&ceid=KR:ko"
                try:
                    res = requests.get(rss, timeout=15)
                    titles = [re.split(r' - | \| ', i.title.get_text())[0] for i in BeautifulSoup(res.text, 'xml').find_all('item')[:25]]
                    if titles:
                        # 🌟 메인 키워드 5개 필터링
                        resp = ai_engine.generate_content(f"{titles}에서 핵심 전략 키워드 5개만 #단어 형태로 뽑아줘.")
                        tags = re.findall(r'#\w+', resp.text)
                        st.markdown("<div class='section-header'>📌 주요 이슈 키워드</div>", unsafe_allow_html=True)
                        st.markdown("".join([f"<span class='issue-tag'>{t}</span>" for t in tags[:5]]), unsafe_allow_html=True)
                        st.pyplot(create_wc(" ".join(titles)))
                    else: st.warning("데이터가 없습니다.")
                except: st.error("통신 오류가 발생했습니다. 다시 시도해 주세요.")

    with t2:
        c1, c2 = st.columns([3, 1])
        s_keyword = c1.text_input("검색 트렌드 키워드", key="s_k")
        s_period = c2.selectbox("기간 설정", ["3일", "7일", "한달", "60일", "분기"], index=2, key="s_p_k")
        if st.button("🔍 검색 AI 분석 시작"):
            rss = f"https://news.google.com/rss/search?q={s_keyword}+추천+반응&hl=ko&gl=KR&ceid=KR:ko"
            res = requests.get(rss, timeout=15)
            titles = [i.title.get_text() for i in BeautifulSoup(res.text, 'xml').find_all('item')[:25]]
            if titles:
                resp = ai_engine.generate_content(f"{titles}에서 대중 관심사 키워드 5개만 #단어로 뽑아줘.")
                tags = re.findall(r'#\w+', resp.text)
                st.markdown("<div class='section-header'>🎯 대중 관심사 해시태그</div>", unsafe_allow_html=True)
                st.markdown("".join([f"<span class='issue-tag'>{t}</span>" for t in tags[:5]]), unsafe_allow_html=True)
                st.pyplot(create_wc(" ".join(titles)))

# 2. 광고주 DB 관리
elif main_menu == "📂 광고주 DB 관리":
    st.header("📂 광고주 DB 관리")
    col1, col2 = st.columns(2)
    with col1:
        up_f = st.file_uploader("💾 백업 파일(XLSX) 업로드", type=['xlsx'])
        if up_f:
            st.session_state.history_db = pd.read_excel(up_f, engine='openpyxl')
            st.success("데이터 로드 완료!")
    with col2:
        # 🌟 백업파일 다운로드 기능
        if not st.session_state.history_db.empty:
            towrite = BytesIO()
            st.session_state.history_db.to_excel(towrite, index=False, engine='openpyxl')
            st.download_button(label="📥 전체 DB 백업 다운로드", data=towrite.getvalue(), file_name=f"AE_Backup_{datetime.date.today()}.xlsx")
    
    st.dataframe(st.session_state.history_db, use_container_width=True)

# 3. 관리 이력 입력
elif main_menu == "📝 관리 이력 입력":
    st.header("📝 관리 이력 입력")
    all_clients = sorted(st.session_state.history_db['광고주명'].dropna().unique().tolist())
    
    with st.form("input_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        in_date = c1.date_input("날짜", datetime.date.today())
        in_name_select = c2.selectbox("광고주 검색/선택", ["직접 입력"] + all_clients)
        
        # 🌟 '직접 입력' 시 검색 매칭
        in_name_text = st.text_input("새 광고주명 입력 (일부 입력 시 기존 업체 자동 매칭)")
        
        # 🌟 네이버 데이터랩 카테고리 적용
        in_cat = st.selectbox("업종 카테고리 (네이버 데이터랩 기준)", NAVER_CATEGORIES)
        in_content = st.text_area("소통 내용")
        
        if st.form_submit_button("💾 데이터 저장하기"):
            final_name = in_name_select
            if in_name_select == "직접 입력":
                matches = [c for c in all_clients if in_name_text in c]
                final_name = matches[0] if matches and in_name_text else in_name_text

            if final_name and in_content:
                new_row = pd.DataFrame({'날짜': [pd.to_datetime(in_date)], '광고주명': [final_name], '소통내용': [in_content], '카테고리': [in_cat]})
                st.session_state.history_db = pd.concat([st.session_state.history_db, new_row], ignore_index=True)
                st.success(f"✅ {final_name} 이력이 저장되었습니다.")

# 4. 내부 소통 이슈 리포트
elif main_menu == "📊 내부 소통 이슈 리포트":
    st.header("📊 내부 소통 이슈 리포트")
    if not st.session_state.history_db.empty:
        client_list = sorted(st.session_state.history_db['광고주명'].dropna().unique().tolist())
        c1, c2, c3 = st.columns(3)
        target = c1.selectbox("광고주 선택", client_list)
        target_cat = c2.selectbox("업종 카테고리", NAVER_CATEGORIES)
        st.session_state.history_db['날짜'] = pd.to_datetime(st.session_state.history_db['날짜'])
        date_range = c3.date_input("분석 기간", [datetime.date.today() - datetime.timedelta(days=30), datetime.date.today()])
        
        # 🌟 상하 배치로 사이즈 확대 및 엑셀 다운로드 추가
        st.markdown(f"<div class='section-header'>💬 내부 소통 이슈 ({target})</div>", unsafe_allow_html=True)
        f_df = st.session_state.history_db[st.session_state.history_db['광고주명'] == target]
        if len(date_range) == 2:
            f_df = f_df[(f_df['날짜'].dt.date >= date_range[0]) & (f_df['날짜'].dt.date <= date_range[1])]
        
        if not f_df.empty:
            st.pyplot(create_wc(" ".join(f_df['소통내용'].astype(str)), height=500))
            towrite_f = BytesIO()
            f_df.to_excel(towrite_f, index=False, engine='openpyxl')
            st.download_button(f"📥 {target} 소통 데이터 추출", towrite_f.getvalue(), f"{target}_issue.xlsx")
        
        st.markdown(f"<div class='section-header'>🌏 {target_cat} 시장 트렌드 매칭</div>", unsafe_allow_html=True)
        if st.button(f"🔗 실시간 {target_cat} 트렌드 확인"):
            with st.spinner("데이터 매칭 중..."):
                rss = f"https://news.google.com/rss/search?q={target_cat}+트렌드+이슈&hl=ko&gl=KR&ceid=KR:ko"
                titles = [i.title.get_text() for i in BeautifulSoup(requests.get(rss).text, 'xml').find_all('item')[:30]]
                if titles:
                    st.pyplot(create_wc(" ".join(titles), height=500))
                    st.info("💡 위/아래 데이터를 비교하여 소구점 일치 여부를 분석하세요.")
    else: st.info("데이터가 없습니다.")
