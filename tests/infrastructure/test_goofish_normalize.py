from katao_xianyu.infrastructure.goofish_gateway import normalize_goofish_response


def test_normalize_json_string_success():
    raw = '{"code":0,"msg":"OK","data":{"product_id":"p1"}}'
    out = normalize_goofish_response(raw)
    assert out["code"] == 0
    assert out["data"]["product_id"] == "p1"


def test_normalize_error_string_body():
    raw = '{"code":500,"msg":"boom"}'
    out = normalize_goofish_response(raw)
    assert out["code"] == 500
    assert out["msg"] == "boom"


def test_normalize_plain_text_failure():
    out = normalize_goofish_response("not-json")
    assert out["code"] == -1
