from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ImportIssueData:
    severity: str
    code: str
    sheet: str
    row: int
    field: str | None
    message: str


class NormalizationError(ValueError):
    def __init__(self, issues: tuple[ImportIssueData, ...]) -> None:
        self.issues = issues
        codes = ", ".join(sorted({issue.code for issue in issues if issue.severity == "ERROR"}))
        super().__init__(f"EVA normalization failed: {codes}")
