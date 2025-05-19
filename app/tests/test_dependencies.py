import importlib
from collections import defaultdict
from pathlib import Path


def test_no_circular_dependencies(settings):
    graph = defaultdict(set)
    circular_dependencies = set()

    n_migrations = 0

    for file in (Path(settings.SITE_ROOT) / "grandchallenge").rglob(
        "**/migrations/*.py"
    ):
        if file.name != "__init__.py":
            n_migrations += 1

            app_name = file.parent.parent.name
            migration_name = file.stem

            migration_module = importlib.import_module(
                f"grandchallenge.{app_name}.migrations.{migration_name}"
            )

            graph[app_name].update(
                d[0] for d in migration_module.Migration.dependencies
            )

    for app, dependencies in graph.items():
        for depencency in dependencies:
            if depencency != app and app in graph.get(depencency, {}):
                circular_dependencies.add(frozenset({app, depencency}))

    assert n_migrations != 0
    assert graph != {}
    assert circular_dependencies == set()
