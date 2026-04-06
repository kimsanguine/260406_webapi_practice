"""기상청 초단기실황 API"""
import datetime
import requests
from pytz import timezone


BASE_URL = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst"

CATEGORY_MAP = {
    "T1H": ("기온", "°C"),
    "REH": ("습도", "%"),
    "RN1": ("1시간 강수량", "mm"),
    "PTY": ("강수 형태", ""),
    "SKY": ("하늘 상태", ""),
    "UUU": ("동서 바람 성분", "m/s"),
    "VVV": ("남북 바람 성분", "m/s"),
    "VEC": ("풍향", "°"),
    "WSD": ("풍속", "m/s"),
}

RAIN_TYPE = {0: "없음", 1: "비", 2: "비/눈", 3: "눈", 5: "빗방울", 6: "빗방울눈날림", 7: "눈날림"}
SKY_COND = {1: "맑음", 3: "구름 많음", 4: "흐림"}


def _get_base_time() -> tuple[str, str]:
    """현재 시각 기준 기상청 base_date, base_time 산출"""
    local_time = datetime.datetime.now(timezone("Asia/Seoul"))
    base_date = local_time.strftime("%Y%m%d")
    # 초단기실황: 매 정시 발표, 45분 후 제공 → 30분 기준으로 이전/현재 시간 선택
    if local_time.minute < 30:
        base_hour = local_time.hour - 1
    else:
        base_hour = local_time.hour
    base_time = f"{base_hour:02d}00"
    return base_date, base_time


def get_weather(api_key: str, nx: int, ny: int) -> dict:
    """
    격자 좌표(nx, ny) 기준 초단기실황 조회.

    Args:
        api_key: 공공데이터포털 서비스 키 (디코딩된 키)
        nx: 예보 지점 X 좌표
        ny: 예보 지점 Y 좌표

    Returns:
        {
            "success": bool,
            "base_date": str,
            "base_time": str,
            "items": [{"category": ..., "name": ..., "value": ..., "unit": ...}],
            "error": str | None
        }
    """
    base_date, base_time = _get_base_time()

    params = {
        "ServiceKey": api_key,
        "pageNo": 1,
        "numOfRows": 10,
        "dataType": "JSON",
        "base_date": base_date,
        "base_time": base_time,
        "nx": nx,
        "ny": ny,
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        return {"success": False, "base_date": base_date, "base_time": base_time, "items": [], "error": str(e)}
    except ValueError:
        return {"success": False, "base_date": base_date, "base_time": base_time, "items": [], "error": "JSON 파싱 오류"}

    header = data.get("response", {}).get("header", {})
    if header.get("resultCode") != "00":
        return {
            "success": False,
            "base_date": base_date,
            "base_time": base_time,
            "items": [],
            "error": header.get("resultMsg", "API 오류"),
        }

    raw_items = data["response"]["body"]["items"]["item"]
    items = []
    for item in raw_items:
        cat = item["category"]
        raw_val = item["obsrValue"]
        name, unit = CATEGORY_MAP.get(cat, (cat, ""))

        # 카테고리별 값 변환
        if cat == "PTY":
            display = RAIN_TYPE.get(int(raw_val), raw_val)
        elif cat == "SKY":
            display = SKY_COND.get(int(raw_val), raw_val)
        else:
            display = raw_val

        items.append({"category": cat, "name": name, "value": display, "unit": unit})

    return {
        "success": True,
        "base_date": base_date,
        "base_time": base_time,
        "items": items,
        "error": None,
    }
