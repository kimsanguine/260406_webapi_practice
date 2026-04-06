"""우체국 주소 검색 API"""
import requests
import xmltodict


BASE_URL = "http://openapi.epost.go.kr/postal/retrieveNewAdressAreaCdService/retrieveNewAdressAreaCdService/getNewAddressListAreaCd"


def search_address(api_key: str, keyword: str, search_type: str = "road") -> dict:
    """
    주소 키워드로 우편번호 및 주소 정보를 조회한다.

    Args:
        api_key: 공공데이터포털 서비스 키 (디코딩된 키)
        keyword: 검색할 주소 (예: "둔산대로 135")
        search_type: "road" (도로명) 또는 "jibun" (지번)

    Returns:
        {
            "success": bool,
            "total": int,
            "results": [{"zipNo": ..., "lnmAdres": ..., "rnAdres": ...}],
            "error": str | None
        }
    """
    params = {
        "ServiceKey": api_key,
        "searchSe": search_type,
        "srchwrd": keyword,
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return {"success": False, "total": 0, "results": [], "error": str(e)}

    try:
        data = xmltodict.parse(response.text)
        header = data["NewAddressListResponse"]["cmmMsgHeader"]

        if header.get("successYN") != "Y":
            return {
                "success": False,
                "total": 0,
                "results": [],
                "error": header.get("errMsg", "API 오류"),
            }

        total = int(header.get("totalCount", 0))
        raw = data["NewAddressListResponse"].get("newAddressListAreaCd", [])

        # 결과가 1건이면 dict, 복수건이면 list로 반환됨
        if isinstance(raw, dict):
            raw = [raw]

        results = [
            {
                "zipNo": item.get("zipNo", ""),
                "lnmAdres": item.get("lnmAdres", ""),
                "rnAdres": item.get("rnAdres", ""),
            }
            for item in raw
        ]

        return {"success": True, "total": total, "results": results, "error": None}

    except Exception as e:
        return {"success": False, "total": 0, "results": [], "error": f"파싱 오류: {e}"}
