from cli import build_parser


def test_cli_parser_defaults():
    args = build_parser().parse_args(["sample.pdf"])
    assert args.pdf == "sample.pdf"
    assert args.force_ocr is False
    assert args.ocr_lang == "eng"
    assert args.min_chars_per_page == 25
