// 마지막 AI 응답의 차트 태그/Lot/Defect 유형을 보고 후속 질문 4개를 만든다

export const INITIAL_QUESTIONS = [
  "M14 CMP 전일 이슈 정리해줘",
  "M14 CMP Area 지금 WIP 현황 알려줘",
  "전체 Lot Recipe 기준으로 수율 분석해줘",
  "TE2FE35 Defect Map 보여줘",
];

const DEFECT_TYPES_ALL = ["PARTICLE", "SCRATCH", "BRIDGE", "PIT", "RESIDUE", "CLUSTER"];

function extractLot(content: string): string {
  const m = content.match(/TE2F[EFC]\d+/);
  return m ? m[0] : "TE2FE35";
}
function extractWafer(content: string): string {
  const m = content.match(/[Ww]afer\s*(\d+)/);
  return m ? m[1] : "5";
}
function extractDefectType(content: string): string {
  return DEFECT_TYPES_ALL.find((t) => content.includes(t)) ?? "PARTICLE";
}

export function getFollowUpSuggestions(content: string): string[] {
  const lot    = extractLot(content);
  const wafer  = extractWafer(content);
  const defect = extractDefectType(content);

  if (content.includes("[DAILY_REPORT:")) {
    return [
      "지금 WIP 현황도 보여줘",
      `${lot} Hold 원인 확인해줘`,
      `${lot} Defect Map 보여줘`,
      "전체 Lot Recipe 기준 수율 분석해줘",
    ];
  }
  if (content.includes("[WIP_STATUS:")) {
    return [
      "M14 CMP 전일 이슈 정리해줘",
      `${lot} Hold 원인 확인해줘`,
      `${lot} Defect Map 보여줘`,
      "전체 Lot Equipment 기준 수율 비교해줘",
    ];
  }
  if (content.includes("[DEFECT_STEP_OVERLAY:")) {
    return [
      `${lot} Defect Map 전체 현황 보여줘`,
      `${lot} ${defect} 수율 이력 분석해줘`,
      `${lot} Wafer ${wafer}번 수율 Chip Kill 분석해줘`,
      "M14 CMP 전일 이슈 정리해줘",
    ];
  }
  if (content.includes("[DEFECT_YIELD_HISTORY:")) {
    return [
      `${lot} Wafer ${wafer}번 Step 간 Defect 비교해줘`,
      `${lot} Defect Map 보여줘`,
      `${lot} 두께 트렌드 분석해줘`,
      "전체 Lot 수율 분석해줘",
    ];
  }
  if (content.includes("[YIELD_DEFECT:")) {
    return [
      `${lot} Wafer ${wafer}번 Step 간 Defect 비교해줘`,
      `${lot} ${defect} Defect Trend 보여줘`,
      `${lot} ${defect} 수율 이력 분석해줘`,
      "전체 Lot Recipe 기준 수율 비교해줘",
    ];
  }
  if (content.includes("[DEFECT_MAP:") || content.includes("[DEFECT_TREND:")) {
    return [
      `${lot} Wafer ${wafer}번 Step 간 Defect 비교해줘`,
      `${lot} ${defect} 수율 이력 분석해줘`,
      `${lot} Wafer ${wafer}번 수율 Chip Kill 분석해줘`,
      "전체 Lot Equipment 기준 수율 비교해줘",
    ];
  }
  if (content.includes("[YIELD_ANALYSIS:")) {
    return [
      "Equipment 기준으로도 수율 비교해줘",
      "Process ID 기준 수율 분석해줘",
      `${lot} Defect Map 보여줘`,
      "M14 CMP 전일 이슈 정리해줘",
    ];
  }
  if (content.includes("[WAFER_MAP:")) {
    return [
      `${lot} 두께 트렌드 분석해줘`,
      `${lot} Defect Map 보여줘`,
      `${lot} Hold 원인 확인해줘`,
      "M14 CMP 전일 이슈 정리해줘",
    ];
  }
  if (content.includes("[TREND_CHART:")) {
    return [
      `${lot} Wafer Map 보여줘`,
      `${lot} Defect Map 보여줘`,
      `${lot} Hold 원인 확인해줘`,
      "M14 CMP 전일 이슈 정리해줘",
    ];
  }
  // Hold 답변 또는 일반 텍스트 응답
  if (content.includes("HOLD") || content.includes("Hold")) {
    return [
      `${lot} Wafer Map 보여줘`,
      `${lot} Defect Map 보여줘`,
      `${lot} 두께 트렌드 분석해줘`,
      "M14 CMP 전일 이슈 정리해줘",
    ];
  }
  return INITIAL_QUESTIONS;
}
