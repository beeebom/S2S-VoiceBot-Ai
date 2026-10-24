"""Typed records extracted from a churn interview.

The schema is deliberately narrow. Every field exists because somebody can act
on it: an engineer reproducing a bug, a PM pricing a win-back offer. Fields that
would only produce a chart were left out.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ChurnReason(str, Enum):
    """Why the user left, in buckets that route to different owners."""

    BUG = "bug"
    MISSING_FEATURE = "missing_feature"
    PRICE = "price"
    USABILITY = "usability"
    PERFORMANCE = "performance"
    COMPETITOR = "competitor"
    NO_LONGER_NEEDED = "no_longer_needed"
    SUPPORT = "support"
    TRUST = "trust"
    UNCLEAR = "unclear"


class Severity(str, Enum):
    BLOCKING = "blocking"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNCLEAR = "unclear"


class ReturnLikelihood(str, Enum):
    """Whether the user would come back, and on what terms."""

    YES_UNCONDITIONAL = "yes_unconditional"
    YES_IF_FIXED = "yes_if_fixed"
    MAYBE = "maybe"
    NO = "no"
    UNCLEAR = "unclear"


class Confidence(BaseModel):
    """How much to trust one extracted field.

    `stated` is the important flag: it separates what the user actually said
    from what the model inferred. An inferred field with a high score is still
    an inference, and a dataset that conflates the two is not worth much.
    """

    score: float = Field(
        ..., ge=0.0, le=1.0, description="0 to 1. How certain this value is."
    )
    stated: bool = Field(
        ...,
        description=(
            "True if the user said this explicitly. False if it was inferred "
            "from context."
        ),
    )
    basis: str = Field(
        ...,
        description=(
            "Short quote or paraphrase from the transcript supporting this "
            "value. Empty string if nothing in the transcript supports it."
        ),
    )


class BugDetail(BaseModel):
    """What an engineer needs to reproduce the problem.

    All optional: most calls will not surface all of it, and a half-filled bug
    report is still useful. Inventing a device string to fill the schema is not.
    """

    surface: Optional[str] = Field(
        None, description="Screen, feature or flow where it happened."
    )
    device: Optional[str] = Field(
        None, description="Device or model, only if the user named it."
    )
    platform: Optional[str] = Field(None, description="iOS, Android, web, desktop.")
    steps: Optional[str] = Field(
        None, description="What the user was doing, in their own terms."
    )
    frequency: Optional[str] = Field(
        None, description="Every time, intermittent, once."
    )


class PriceDetail(BaseModel):
    """The numbers that make a pricing decision possible."""

    current_price: Optional[str] = Field(
        None, description="What they were paying, if mentioned."
    )
    acceptable_price: Optional[str] = Field(
        None,
        description=(
            "The price they said they would have stayed at. This is the single "
            "most valuable field in the record - only fill it if they named a "
            "number or a clear range."
        ),
    )
    competitor: Optional[str] = Field(
        None, description="Who they switched to, if named."
    )


class ChurnRecord(BaseModel):
    """One call, as a row.

    Produced by `extract_record`. Treat `*_confidence` as part of the data, not
    metadata: a record whose reason confidence is low should not be counted in
    an aggregate without saying so.
    """

    reason: ChurnReason
    reason_confidence: Confidence

    severity: Severity
    severity_confidence: Confidence

    return_likelihood: ReturnLikelihood
    return_condition: Optional[str] = Field(
        None,
        description=(
            "What would have to change for them to come back, in one sentence. "
            "Null if they named no condition."
        ),
    )
    return_confidence: Confidence

    bug: Optional[BugDetail] = Field(
        None, description="Only when reason is bug or performance."
    )
    price: Optional[PriceDetail] = Field(
        None, description="Only when reason is price or competitor."
    )

    summary: str = Field(
        ...,
        description="One sentence a PM could read in a list of fifty.",
    )
    verbatim: List[str] = Field(
        default_factory=list,
        description=(
            "Up to three exact quotes from the user worth showing a human. "
            "Copied word for word, never paraphrased."
        ),
    )

    interview_quality: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=(
            "Did this call actually surface anything? Low means the user was "
            "terse, distracted or hung up early - the row exists but should "
            "carry little weight."
        ),
    )
    followup_needed: bool = Field(
        ...,
        description="True if a human should call this person back.",
    )

    @property
    def is_actionable(self) -> bool:
        """Whether this record supports a decision on its own.

        The threshold is deliberately strict: an actionable row needs a reason
        the user actually stated and a call that went somewhere. Everything
        else is context, not evidence.
        """
        return (
            self.reason is not ChurnReason.UNCLEAR
            and self.reason_confidence.stated
            and self.reason_confidence.score >= 0.6
            and self.interview_quality >= 0.5
        )

    @property
    def is_save_opportunity(self) -> bool:
        """Whether somebody could try to win this user back today."""
        return (
            self.return_likelihood
            in (ReturnLikelihood.YES_UNCONDITIONAL, ReturnLikelihood.YES_IF_FIXED)
            and self.return_condition is not None
        )
