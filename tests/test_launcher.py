from kenshi_test.launcher import mod_warning_button


def test_process_exit_filter_is_fail_closed():
    from kenshi_test.launcher import process_may_be_running
    assert not process_may_be_running(3)
    assert process_may_be_running(259)
    assert process_may_be_running(None)


def warning(title, text, identifier=6, label="是(&Y)"):
    return {"title": title, "children": [
        {"class": "Static", "id": 65535, "text": text},
        {"class": "Button", "id": identifier, "text": label},
    ]}


def test_observed_chinese_warning_is_recognized():
    dialog = warning("mod警告", "一个或多个mod已丢失或顺序错误。\n是否继续？")
    assert mod_warning_button(dialog)["id"] == 6


def test_english_equivalent_is_recognized():
    dialog = warning("Mods warning", "One or more mods are missing or in incorrect order.",
                     1, "OK")
    assert mod_warning_button(dialog)["id"] == 1


def test_other_mod_warning_and_negative_button_are_not_accepted():
    assert mod_warning_button(warning("Mod Warning", "Delete this mod?")) is None
    negative = warning("mod警告", "一个或多个mod已丢失或顺序错误", 7, "否(&N)")
    assert mod_warning_button(negative) is None
    assert mod_warning_button(warning("Security Warning", "一个或多个mod已丢失或顺序错误")) is None
def test_attach_accepts_one_parent_child_tree_but_not_independent_games():
    from kenshi_test.launcher import launcher_roots

    assert launcher_roots({10: (1, "kenshi_x64.exe"), 11: (10, "kenshi_x64.exe")}) == {10}
    assert launcher_roots({10: (1, "kenshi_x64.exe"), 11: (2, "kenshi_x64.exe")}) == {10, 11}
