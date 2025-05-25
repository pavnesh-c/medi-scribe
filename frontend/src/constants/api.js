export const API_BASE_URL = 'http://127.0.0.1:5000/api/v1'

export const API_ENDPOINTS = {
  LIVE_CONVERSATION: {
    START: `${API_BASE_URL}/live-conversation/start`,
    END: (conversationId) => `${API_BASE_URL}/live-conversation/${conversationId}/end`,
    STATS: (conversationId) => `${API_BASE_URL}/live-conversation/${conversationId}/stats`,
    UTTERANCE: (conversationId) => `${API_BASE_URL}/live-conversation/${conversationId}/utterance`
  },
  UPLOAD: {
    INIT: `${API_BASE_URL}/upload/init`,
    CHUNK: `${API_BASE_URL}/upload/chunk`,
    FINISH: `${API_BASE_URL}/upload/finish`
  }
} 