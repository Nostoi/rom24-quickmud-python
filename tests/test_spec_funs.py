from mud.spec_funs import get_spec_fun, register_spec_fun, spec_fun_registry


def test_case_insensitive_lookup() -> None:
    called: list[tuple[object, ...]] = []

    def dummy(*args: object) -> None:  # placeholder spec_fun
        called.append(args)
    prev = dict(spec_fun_registry)
    try:
        register_spec_fun("Spec_Test", dummy)

        assert get_spec_fun("spec_test") is dummy
        assert get_spec_fun("SPEC_TEST") is dummy
        assert called == []
    finally:
        spec_fun_registry.clear()
        spec_fun_registry.update(prev)
