export interface YoutubeCommentSummary {
  author: string;
  published_at: string;
  original: string;
  processed: string;
  action: 'PASS' | 'MASK' | 'AUTO_HIDE';
  risk_score: number;
  violation_tags: string[]; // e.g., ["AI_AGGRESSION", "SYSTEM_KEYWORD"]
}

export interface YoutubeAnalysisResponse {
  video_info: {
    title?: string;
    channel?: string;
    [key: string]: string | undefined;
  };
  stats: {
    total_comments?: number;
    filtered_count?: number;
    [key: string]: number | undefined;
  };
  results: YoutubeCommentSummary[];
}

export interface AppSettings {
  intensity: number; // 1~5
  modules: {
    criticism: boolean;   // 유튜버 대상 비난
    conflict: boolean;    // 갈등 조장/어그로
    gaslighting: boolean; // 신뢰도 저하/가스라이팅
    sexual: boolean;      // 성희롱/선정적 괴롭힘
    relevance: boolean;   // 주제 연관성 및 비판 분석
  };
  whiteList: string[];
  blackList: string[];
}