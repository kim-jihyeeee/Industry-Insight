import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import datetime, requests, re
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. 페이지 설정
st.set_page_config(page_title="AE Total Tool v13.3", layout="wide")

# 🌟 Gemini API 설정
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
    st.session_state.history_db = pd.DataFrame(columns=['날짜', '광고주명', '소통내용', '카테고리'])

# UI 스타일
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; background-color: #FFB300; color: white; font-weight: bold; height: 3em; }
    .issue-tag { display: inline-block; padding: 8px 15px; margin: 5px; background-color: #f0f2f6; border-radius: 15px; font-weight: bold; color: #333; font-size: 0.9em; }
    .section-header { font-size: 1.2em; font-weight: bold; margin: 20px 0 10px 0; border-left: 5px solid #FFB300; padding-left: 10px; }
    </style>
""", unsafe_allow_html=True)

def create_wc(text):
    if not text or not text.strip(): return None
    wc = WordCloud(font_path=FONT_PATH, width=1000, height=500, background_color='white', colormap='Dark2').generate(text)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wc, interpolation='bilinear'); ax.axis('off')
    return fig

# --- 사이드바 메뉴 ---
with st.sidebar:
    st.title("🚀 AE Total Tool v13.3")
    main_menu = st.radio("메뉴 선택", ["🌐 AI Trend Radar", "📂 광고주 DB 관리", "📝 관리 이력 입력", "📊 내부 소통 이슈 리포트"])

# 1. AI Trend Radar
if main_menu == "🌐 AI Trend Radar":
    st.title("🌐 AI Trend Radar")
    t1, t2 = st.tabs(["📰 뉴스 분석", "🔍 검색 분석"])
    
    with t1:
        c1, c2 = st.columns([3, 1])
        n_keyword = c1.text_input("분석 키워드", placeholder="예: 단백질 쉐이크", key="n_k")
        # 🌟 기간 옵션 확장: 3일/7일/한달/60일/분기
        n_period = c2.selectbox("기간 설정", ["3일", "7일", "한달", "60일", "분기"], index=2, key="n_p")
        
        if st.button("🚀 트렌드 분석 시작"):
            with st.spinner("시장 데이터를 분석 중입니다..."):
                rss = f"https://news.google.com/rss/search?q={n_keyword}&hl=ko&gl=KR&ceid=KR:ko"
                try:
                    res = requests.get(rss, timeout=10)
                    titles = [re.split(r' - | \| ', i.title.get_text())[0] for i in BeautifulSoup(res.text, 'xml').find_all('item')[:20]]
                    if titles:
                        resp = ai_engine.generate_content(f"{titles}에서 주요 트렌드 키워드 5개만 #단어 형태로 추출해줘.")
                        tags = re.findall(r'#\w+', resp.text)
                        st.markdown("<div class='section-header'>🔥 실시간 시장 이슈</div>", unsafe_allow_html=True)
                        st.markdown("".join([f"<span class='issue-tag'>{t}</span>" for t in tags[:5]]), unsafe_allow_html=True)
                        st.pyplot(create_wc(" ".join(titles)))
                    else: st.warning("검색 결과가 없습니다.")
                except: st.error("통신 오류가 발생했습니다.")

    with t2:
        c1, c2 = st.columns([3, 1])
        s_keyword = c1.text_input("검색어 입력", key="s_k")
        s_period = c2.selectbox("기간 설정", ["3일", "7일", "한달", "60일", "분기"], index=2, key="s_p")
        if st.button("🔍 검색어 기반 시각화"):
            rss = f"https://news.google.com/rss/search?q={s_keyword}+리뷰+추천&hl=ko&gl=KR&ceid=KR:ko"
            titles = [i.title.get_text() for i in BeautifulSoup(requests.get(rss).text, 'xml').find_all('item')[:20]]
            if titles: st.pyplot(create_wc(" ".join(titles)))

# 2. 광고주 DB 관리
elif main_menu == "📂 광고주 DB 관리":
    st.header("📂 광고주 DB 관리")
    up_f = st.file_uploader("파일 업로드 (XLSX)", type=['xlsx'])
    if up_f:
        st.session_state.history_db = pd.read_excel(up_f, engine='openpyxl')
        st.success("DB 로드 완료!")
    st.dataframe(st.session_state.history_db, use_container_width=True)

# 3. 관리 이력 입력
elif main_menu == "📝 관리 이력 입력":
    st.header("📝 관리 이력 입력")
    # 🌟 기존 DB 내 모든 광고주 리스트 추출
    all_clients = sorted(st.session_state.history_db['광고주명'].dropna().unique().tolist())
    
    with st.form("input_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        in_date = col1.date_input("날짜", datetime.date.today())
        in_name_select = col2.selectbox("광고주 검색/선택 (목록에 있으면 선택)", ["직접 입력"] + all_clients)
        
        # 🌟 검색 및 자동완성 기능을 위한 텍스트 필드
        in_name_text = st.text_input("새 광고주명 입력 (일부 입력 시 기존 DB 대조 자동 완성)")
        
        in_cat = st.selectbox("카테고리 설정", ["식품", "뷰티", "건강기능식품", "패션", "가전/IT", "기타"])
        in_content = st.text_area("소통 내용")
        
        if st.form_submit_button("💾 저장하기"):
            # 🌟 검색/자동완성 로직: 텍스트 입력이 기존 리스트와 매칭되면 해당 이름으로 고정
            final_name = in_name_select
            if in_name_select == "직접 입력":
                # 입력한 텍스트가 기존 광고주 리스트에 포함되어 있는지 확인
                matches = [c for c in all_clients if in_name_text in c]
                final_name = matches[0] if matches and in_name_text else in_name_text

            if final_name and in_content:
                new_row = pd.DataFrame({'날짜': [pd.to_datetime(in_date)], '광고주명': [final_name], '소통내용': [in_content], '카테고리': [in_cat]})
                st.session_state.history_db = pd.concat([st.session_state.history_db, new_row], ignore_index=True)
                st.success(f"✅ {final_name} 이력이 저장되었습니다.")
            else:
                st.error("필수 정보를 입력해 주세요.")

# 4. 내부 소통 이슈 리포트
elif main_menu == "📊 내부 소통 이슈 리포트":
    st.header("📊 내부 소통 이슈 리포트")
    if not st.session_state.history_db.empty:
        client_list = sorted(st.session_state.history_db['광고주명'].dropna().unique().tolist())
        c1, c2, c3 = st.columns(3)
        target = c1.selectbox("분석 대상 광고주", client_list)
        
        # 🌟 광고주 카테고리 선택 (시장 트렌드 대조용)
        target_cat = c2.selectbox("비교할 업종 카테고리", ["식품", "뷰티", "건강기능식품", "패션", "가전/IT", "기타"])
        
        st.session_state.history_db['날짜'] = pd.to_datetime(st.session_state.history_db['날짜'])
        date_range = c3.date_input("분석 기간", [datetime.date.today() - datetime.timedelta(days=30), datetime.date.today()])
        
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.markdown(f"<div class='section-header'>💬 내부 소통 이슈 ({target})</div>", unsafe_allow_html=True)
            f_df = st.session_state.history_db[st.session_state.history_db['광고주명'] == target]
            if len(date_range) == 2:
                f_df = f_df[(f_df['날짜'].dt.date >= date_range[0]) & (f_df['날짜'].dt.date <= date_range[1])]
            
            if not f_df.empty:
                st.pyplot(create_wc(" ".join(f_df['소통내용'].astype(str))))
            else: st.warning("선택 기간 내 소통 데이터가 없습니다.")
            
        with col_right:
            st.markdown(f"<div class='section-header'>🌏 {target_cat} 시장 트렌드 매칭</div>", unsafe_allow_html=True)
            # 🌟 실시간 시장 데이터 수집 버튼
            if st.button(f"🔗 실시간 {target_cat} 이슈 확인"):
                with st.spinner("트렌드 매칭 중..."):
                    rss = f"https://news.google.com/rss/search?q={target_cat}+트렌드+이슈&hl=ko&gl=KR&ceid=KR:ko"
                    titles = [i.title.get_text() for i in BeautifulSoup(requests.get(rss).text, 'xml').find_all('item')[:20]]
                    if titles:
                        st.pyplot(create_wc(" ".join(titles)))
                        st.info("💡 좌측 소통 내용과 우측 업계 이슈의 일치 여부를 분석하여 제안을 고도화하세요.")
    else: st.info("DB에 저장된 데이터가 없습니다.")
