from typing import List, Union, Optional
from pydantic import BaseModel

class RuleItem(BaseModel):
    ruleId: Union[int, str]
    rule: str

RuleListType = Union[List[str], List[RuleItem]]
class ParameterRule(BaseModel):
    id: Union[int, str]
    name: Optional[str] = None
    ruleList: RuleListType

class AuditRequest(BaseModel):
    audioUrl: str
    transcription: Optional[str] = None
    sampleId: Optional[str] = None
    audioFileId: Optional[str] = None
    userUuid: Optional[str] = None
    parameter: List[ParameterRule]


class SingleRuleRequest(BaseModel):
    ruleId: int
    rule: str
    transcript: str

class SingleRuleResponse(BaseModel):
    ruleId: int
    rule: str
    result: str
    reason: str
