import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import datetime, requests, re
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. 페이지 설정
st.set_page_config(page_title="AE Industry Insight v1.6", layout="wide", initial_sidebar_state="auto")

# 🌟 Gemini API 설정
API_KEY = "AQ.Ab8RN6Lc9LYyyyi-oE7eVOZfjfe8AKJIQ8u3SnPmUce-LjoZRw"

@st.cache_resource
def init_ai():
    if not API_KEY: return None
    try:
        genai.configure(api_key=API_KEY)
        return genai.GenerativeModel('gemini-pro')
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

# 네이버 데이터랩 기준 카테고리
NAVER_CATEGORIES = {
    "패션의류": ["여성의류", "남성의류", "캐주얼", "언더웨어/잠옷"],
    "패션잡화": ["신발", "가방", "지갑/벨트", "시계/쥬얼리", "패션소품"],
    "화장품/미용": ["스킨케어", "메이크업", "헤어케어", "바디케어", "향수", "네일케어"],
    "디지털/가전": ["주방가전", "생활가전", "계절가전", "모바일/PC", "영상/음향가전"],
    "식품": ["농/수/축산물", "반찬/가공식품", "음료", "과자/베이커리", "건강식품"],
    "스포츠/레저": ["골프", "캠핑/낚시", "등산", "헬스/요가", "수영/스포츠의류"],
    "생활/건강": ["주방/욕실용품", "세탁/생활용품", "반려동물", "의료기기/건강용품"]
}

# 세션 초기화
if 'history_db' not in st.session_state: 
    st.session_state.history_db = pd.DataFrame(columns=['날짜', '광고주명', '소통내용', '핵심키워드'])

# UI 스타일
st.markdown("""
    <style>
    header[data-testid="stHeader"] { visibility: visible; } 
    .stButton>button { width: 100%; border-radius: 8px; background-color: #FFB300; color: white; font-weight: bold; height: 3.5em; }
    .ai-report-card { padding: 25px; background-color: #F8F9FA; border-radius: 12px; border-left: 10px solid #FFB300; margin-bottom: 25px; line-height: 1.8; color: #333; }
    .menu-header { font-size: 1.1em; font-weight: bold; color: #FFB300; margin-top: 30px; border-bottom: 2px solid #eee; padding-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("🚀 Industry Insight v1.6")
    st.markdown('<p class="menu-header">📋 메뉴 선택</p>', unsafe_allow_html=True)
    main_menu = st.radio("항목 선택", 
        ["업종별 트렌드 체크", "가망 광고주 분석/제안", "광고주 DB/이력 관리", "소통 키워드 분석"],
        label_visibility="collapsed")

# --- [기능 1: 업종별 트렌드 체크] ---
if main_menu == "업종별 트렌드 체크":
    st.header("📈 업종별 이슈 마인드맵 분석")
    c1, c2 = st.columns(2)
    with c1: m_cat = st.selectbox("대분류", list(NAVER_CATEGORIES.keys()))
    with c2: s_cat = st.selectbox("상세 카테고리", NAVER_CATEGORIES[m_cat])
    
    if st.button(f"🚀 {s_cat} 마인드맵 분석 시작"):
        with st.spinner("최신 데이터 수집 중..."):
            rss = f"https://news.google.com/rss/search?q={s_cat}+트렌드+이슈&hl=ko&gl=KR&ceid=KR:ko"
            titles = [re.split(r' - | \| ', i.title.get_text())[0] for i in BeautifulSoup(requests.get(rss).text, 'xml').find_all('item')[:15]]
            if titles:
                if ai_engine:
                    resp = ai_engine.generate_content(f"{s_cat} 업종의 최근 트렌드 {titles}를 기반으로 마케팅 전략을 제안해줘.")
                    st.markdown(f'<div class="ai-report-card"><b>🤖 AI 전략 리포트</b><br><br>{resp.text}</div>', unsafe_allow_html=True)
                wc = WordCloud(font_path=FONT_PATH, width=1000, height=600, background_color='white', colormap='tab10').generate(" ".join(titles))
                fig, ax = plt.subplots(figsize=(12, 7)); ax.imshow(wc); ax.axis('off'); st.pyplot(fig)
                buf = BytesIO(); fig.savefig(buf, format="png")
                st.download_button("📥 이미지 저장", buf.getvalue(), f"{s_cat}_트렌드.png", "image/png")

# --- [기능 2: 가망 광고주 분석/제안] ---
elif main_menu == "가망 광고주 분석/제안":
    st.header("🎯 URL 기반 가망 광고주 맞춤 제안")
    t_url = st.text_input("가망 광고주 URL 입력", placeholder="https://...")
    t_cat = st.selectbox("매칭 카테고리 선택", [f"{k} > {v}" for k, vv in NAVER_CATEGORIES.items() for v in vv])
    
    if st.button("💡 제안 전략 생성"):
        if not t_url: st.warning("URL을 입력해 주세요.")
        else:
            with st.spinner("시장 데이터 매칭 및 분석 중..."):
                brand = t_url.split("//")[-1].split(".")[0]
                if "naver" in brand: brand = t_url.split("/")[-1]
                rss = f"https://news.google.com/rss/search?q={brand}+{t_cat.split(' > ')[1]}&hl=ko&gl=KR&ceid=KR:ko"
                news = [i.title.get_text() for i in BeautifulSoup(requests.get(rss).text, 'xml').find_all('item')[:12]]
                if ai_engine:
                    prompt = f"광고주: {brand}, 업종: {t_cat}, 최신이슈: {news}. AE로서 분석 및 제안 전략을 작성해줘."
                    resp = ai_engine.generate_content(prompt)
                    st.markdown(f'<div class="ai-report-card"><b>💡 {brand} 맞춤 제안</b><br><br>{resp.text}</div>', unsafe_allow_html=True)

# --- [기능 3: 광고주 DB/이력 관리] ---
elif main_menu == "광고주 DB/이력 관리":
    st.header("📂 데이터 관리 및 복구")
    
    with st.expander("📝 실시간 소통 이력 입력"):
        with st.form("input_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            name = c1.text_input("광고주명")
            date = c2.date_input("날짜", datetime.date.today())
            content = st.text_area("소통 내용")
            tag = st.text_input("핵심 키워드")
            if st.form_submit_button("저장"):
                new_row = pd.DataFrame([[date, name, content, tag]], columns=['날짜', '광고주명', '소통내용', '핵심키워드'])
                st.session_state.history_db = pd.concat([st.session_state.history_db, new_row], ignore_index=True)
                st.success("저장 완료")

    st.divider()
    
    up_f = st.file_uploader("💾 백업 파일 업로드 (XLSX)", type=['xlsx'])
    if up_f:
        try:
            df = pd.read_excel(up_f, engine='openpyxl')
            # 날짜 형식 정리
            if '날짜' in df.columns:
                df['날짜'] = pd.to_datetime(df['날짜']).dt.date
            st.session_state.history_db = df
            st.success("✅ 기존 데이터 복구가 완료되었습니다!")
        except Exception as e: st.error(f"파일 로드 실패: {e}")

    if not st.session_state.history_db.empty:
        st.dataframe(st.session_state.history_db, use_container_width=True)
        # 엑셀 저장 (xlsxwriter 엔진 명시)
        towrite = BytesIO()
        try:
            st.session_state.history_db.to_excel(towrite, index=False, engine='xlsxwriter')
            st.download_button("📥 현재 DB 백업 다운로드", towrite.getvalue(), "AE_Insight_Backup.xlsx")
        except:
            st.session_state.history_db.to_excel(towrite, index=False, engine='openpyxl')
            st.download_button("📥 현재 DB 백업 다운로드 (오류대비용)", towrite.getvalue(), "AE_Insight_Backup.xlsx")

# --- [기능 4: 소통 키워드 분석] ---
elif main_menu == "소통 키워드 분석":
    st.header("📊 광고주 소통 키워드 분석")
    if st.session_state.history_db.empty:
        st.info("관리 메뉴에서 데이터를 먼저 입력하거나 파일을 업로드하세요.")
    else:
        target = st.selectbox("분석할 광고주 선택", sorted(st.session_state.history_db['광고주명'].unique()))
        period = st.select_slider("분석 기간 설정 (최근 n일)", options=[7, 30, 60, 90, 180, 365], value=90)
        
        # 필터링 로직
        df = st.session_state.history_db.copy()
        df['날짜'] = pd.to_datetime(df['날짜']).dt.date
        limit_date = datetime.date.today() - datetime.timedelta(days=period)
        f_df = df[(df['광고주명'] == target) & (df['날짜'] >= limit_date)]
        
        if not f_df.empty:
            st.subheader(f"🔍 {target} 핵심 소통 마인드맵")
            text = " ".join(f_df['소통내용'].fillna('') + " " + f_df['핵심키워드'].fillna(''))
            if len(text.strip()) > 5:
                wc = WordCloud(font_path=FONT_PATH, width=1000, height=500, background_color='white', colormap='coolwarm').generate(text)
                fig, ax = plt.subplots(figsize=(12, 6)); ax.imshow(wc); ax.axis('off'); st.pyplot(fig)
                
                # 이미지 저장 버튼 부활
                buf = BytesIO(); fig.savefig(buf, format="png")
                st.download_button("📥 분석 이미지 저장", buf.getvalue(), f"{target}_소통분석.png", "image/png")
            else: st.warning("분석할 텍스트 내용이 충분하지 않습니다.")
        else: st.warning(f"선택한 {period}일 기간 내에 데이터가 없습니다.")
