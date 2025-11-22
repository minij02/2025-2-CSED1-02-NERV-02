import axios from 'axios';
import type { YoutubeAnalysisResponse } from './types';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const client = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

// --- MOCK DATA ---
const MOCK_DATA: YoutubeAnalysisResponse = {
  video_info: {
    title: "Pixel 7 Review: The Best Android Phone?",
    channel: "Tech Reviewer",
  },
  stats: {
    total_comments: 120,
    filtered_count: 15,
  },
  results: [
    {
      author: "@TheDiscfanatic",
      published_at: "1 minute ago",
      original: "Was glad to see the Pixel 7 win those two awards...",
      processed: "Was glad to see the Pixel 7 win those two awards...",
      action: "PASS",
      risk_score: 0.05,
      violation_tags: [],
    },
    {
      author: "@Hater123",
      published_at: "5 minutes ago",
      original: "야이 개새끼야 ㅋㅋ 니네 집 주소 다 털었다",
      processed: "야이 **** ㅋㅋ 니네 집 주소 다 털었다",
      action: "AUTO_HIDE",
      risk_score: 0.98,
      violation_tags: ["SYSTEM_KEYWORD", "AI_AGGRESSION"],
    },
    {
      author: "@Spammer",
      published_at: "10 minutes ago",
      original: "돈 버는 법 알려드림. 링크 클릭 -> http://...",
      processed: "돈 버는 법 알려드림. 링크 클릭 -> http://...",
      action: "MASK",
      risk_score: 0.85,
      violation_tags: ["AI_SPAM"],
    },
  ],
};

// --- API FUNCTIONS ---

export const fetchAnalysis = async (videoId: string): Promise<YoutubeAnalysisResponse> => {
  // 로컬 개발 환경이거나 videoId가 테스트용이면 Mock 데이터 반환
  if (!import.meta.env.PROD || videoId === 'test_video_id') {
    console.log(`[Mock API] Fetching analysis for ${videoId}`);
    await new Promise((resolve) => setTimeout(resolve, 800)); // 0.8초 딜레이 시뮬레이션
    return MOCK_DATA;
  }

  // 실제 API 호출
  const response = await client.post(`/api/workflow/analyze-youtube`, null, {
    params: { video_id: videoId, max_pages: 1 },
  });
  return response.data;
};