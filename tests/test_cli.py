from cli import build_parser


def test_cli_parser_defaults():
    args = build_parser().parse_args(["sample.pdf"])
    assert args.pdf == "sample.pdf"
    assert args.force_ocr is False
    assert args.ocr_lang == "eng"
    assert args.min_chars_per_page == 25
    assert args.format == "zip"
    assert args.deck_name == "PDF Imports"
    assert args.no_subdecks is False


def test_cli_parser_apkg_flags():
    args = build_parser().parse_args(
        ["sample.pdf", "--format", "apkg", "--deck-name", "Pharma", "--no-subdecks"]
    )
    assert args.format == "apkg"
    assert args.deck_name == "Pharma"
    assert args.no_subdecks is True
