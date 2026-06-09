import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px


# =========================
# 기본 설정
# =========================

st.set_page_config(
    page_title="글로벌 시가총액 Top 10 주식 대시보드",
    page_icon="📈",
    layout="wide"
)

st.title("📈 글로벌 시가총액 Top 10 주식 대시보드")
st.write(
    "Yahoo Finance 데이터를 활용해 글로벌 대형주의 최근 10년 주가 흐름을 시각화합니다."
)


# =========================
# 종목 목록
# =========================
# 시가총액 순위는 시간이 지나면 바뀔 수 있으므로,
# 연습용으로는 여기 리스트만 바꿔가며 사용하면 됩니다.

COMPANIES = {
    "NVIDIA": "NVDA",
    "Apple": "AAPL",
    "Microsoft": "MSFT",
    "Alphabet": "GOOGL",
    "Amazon": "AMZN",
    "Saudi Aramco": "2222.SR",
    "Meta Platforms": "META",
    "Broadcom": "AVGO",
    "TSMC": "TSM",
    "Tesla": "TSLA",
}


# =========================
# 데이터 다운로드 함수
# =========================

@st.cache_data(ttl=3600)
def load_stock_data(ticker_dict):
    """
    yfinance를 이용해 여러 종목의 최근 10년 주가 데이터를 가져오는 함수
    """
    price_data = {}

    for company, ticker in ticker_dict.items():
        try:
            data = yf.download(
                ticker,
                period="10y",
                interval="1d",
                progress=False,
                auto_adjust=False
            )

            if data.empty:
                continue

            # Adj Close가 있으면 조정종가 사용
            # 없으면 Close 사용
            if "Adj Close" in data.columns:
                price_data[company] = data["Adj Close"]
            else:
                price_data[company] = data["Close"]

        except Exception as e:
            st.warning(f"{company} 데이터를 불러오지 못했습니다: {e}")

    prices = pd.DataFrame(price_data)

    # 모든 값이 비어 있는 날짜 제거
    prices = prices.dropna(how="all")

    return prices


# =========================
# 보조 계산 함수
# =========================

def normalize_prices(prices):
    """
    첫 거래일 가격을 100으로 맞춰서 비교 가능한 지수 형태로 변환
    """
    return prices / prices.ffill().bfill().iloc[0] * 100


def calculate_cumulative_return(prices):
    """
    누적 수익률 계산
    """
    return (prices / prices.ffill().bfill().iloc[0] - 1) * 100


def calculate_mdd(series):
    """
    최대 낙폭, Maximum Drawdown 계산
    """
    series = series.dropna()

    if series.empty:
        return None

    rolling_max = series.cummax()
    drawdown = (series / rolling_max - 1) * 100

    return drawdown.min()


def make_summary_table(prices):
    """
    종목별 요약 통계표 생성
    """
    rows = []

    for company in prices.columns:
        series = prices[company].dropna()

        if series.empty:
            continue

        start_price = series.iloc[0]
        latest_price = series.iloc[-1]
        cumulative_return = (latest_price / start_price - 1) * 100
        mdd = calculate_mdd(series)

        rows.append({
            "기업": company,
            "시작일": series.index[0].strftime("%Y-%m-%d"),
            "최근일": series.index[-1].strftime("%Y-%m-%d"),
            "시작 가격": round(start_price, 2),
            "최근 가격": round(latest_price, 2),
            "누적 수익률(%)": round(cumulative_return, 2),
            "최대 낙폭 MDD(%)": round(mdd, 2),
        })

    return pd.DataFrame(rows)


# =========================
# 사이드바
# =========================

st.sidebar.header("⚙️ 설정")

selected_companies = st.sidebar.multiselect(
    "표시할 기업 선택",
    options=list(COMPANIES.keys()),
    default=list(COMPANIES.keys())
)

chart_type = st.sidebar.radio(
    "그래프 유형",
    ["기준점 100 비교", "누적 수익률", "조정종가"]
)

show_ma = st.sidebar.checkbox("200일 이동평균 표시", value=False)


# =========================
# 데이터 불러오기
# =========================

with st.spinner("Yahoo Finance에서 데이터를 불러오는 중입니다..."):
    all_prices = load_stock_data(COMPANIES)

if all_prices.empty:
    st.error("주가 데이터를 불러오지 못했습니다.")
    st.stop()

prices = all_prices[selected_companies]

if prices.empty:
    st.warning("선택된 종목이 없습니다.")
    st.stop()


# =========================
# 메트릭 표시
# =========================

summary_df = make_summary_table(prices)

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("분석 종목 수", f"{len(selected_companies)}개")

with col2:
    st.metric("분석 기간", "최근 10년")

with col3:
    best_company = summary_df.sort_values("누적 수익률(%)", ascending=False).iloc[0]
    st.metric(
        "누적 수익률 1위",
        best_company["기업"],
        f'{best_company["누적 수익률(%)"]}%'
    )


# =========================
# 그래프용 데이터 만들기
# =========================

if chart_type == "기준점 100 비교":
    chart_data = normalize_prices(prices)
    y_label = "기준점 100 지수"
    title = "최근 10년 주가 변화 비교: 시작점을 100으로 환산"

elif chart_type == "누적 수익률":
    chart_data = calculate_cumulative_return(prices)
    y_label = "누적 수익률(%)"
    title = "최근 10년 누적 수익률 비교"

else:
    chart_data = prices
    y_label = "조정종가"
    title = "최근 10년 조정종가 변화"


chart_data = chart_data.reset_index()

# yfinance에서 Date 인덱스 이름이 없을 수 있어 처리
if "Date" not in chart_data.columns:
    chart_data = chart_data.rename(columns={chart_data.columns[0]: "Date"})


long_df = chart_data.melt(
    id_vars="Date",
    var_name="기업",
    value_name="값"
)


# =========================
# Plotly 그래프
# =========================

fig = px.line(
    long_df,
    x="Date",
    y="값",
    color="기업",
    title=title,
    labels={
        "Date": "날짜",
        "값": y_label,
        "기업": "기업"
    }
)

fig.update_layout(
    height=650,
    hovermode="x unified",
    legend_title_text="기업",
    xaxis_title="날짜",
    yaxis_title=y_label
)

st.plotly_chart(fig, use_container_width=True)


# =========================
# 이동평균선
# =========================

if show_ma:
    st.subheader("📉 200일 이동평균선")

    ma_data = prices.rolling(window=200).mean().reset_index()

    if "Date" not in ma_data.columns:
        ma_data = ma_data.rename(columns={ma_data.columns[0]: "Date"})

    ma_long_df = ma_data.melt(
        id_vars="Date",
        var_name="기업",
        value_name="200일 이동평균"
    )

    ma_fig = px.line(
        ma_long_df,
        x="Date",
        y="200일 이동평균",
        color="기업",
        title="200일 이동평균선",
        labels={
            "Date": "날짜",
            "200일 이동평균": "가격",
            "기업": "기업"
        }
    )

    ma_fig.update_layout(
        height=550,
        hovermode="x unified"
    )

    st.plotly_chart(ma_fig, use_container_width=True)


# =========================
# 요약 통계표
# =========================

st.subheader("📊 종목별 요약 통계")

st.dataframe(
    summary_df.sort_values("누적 수익률(%)", ascending=False),
    use_container_width=True
)


# =========================
# 원본 데이터 보기
# =========================

with st.expander("원본 주가 데이터 보기"):
    st.dataframe(prices.tail(100), use_container_width=True)


# =========================
# CSV 다운로드
# =========================

csv = prices.to_csv().encode("utf-8-sig")

st.download_button(
    label="📥 주가 데이터 CSV 다운로드",
    data=csv,
    file_name="global_top10_stock_prices.csv",
    mime="text/csv"
)


# =========================
# 안내 문구
# =========================

st.caption(
    "데이터 출처: Yahoo Finance / yfinance. "
    "Saudi Aramco는 2019년 상장 종목이므로 10년 전체 데이터가 없을 수 있습니다."
)
