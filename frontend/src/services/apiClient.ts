import axios from "axios"

export const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "",
  timeout: 300000, // Increased to 5 minutes for local Ollama processing
  headers: {
    "Content-Type": "application/json",
  },
})

apiClient.interceptors.request.use(
  (config) => {
    console.log(`[API Request Started] ${config.method?.toUpperCase()} ${config.url}`)
    return config
  },
  (error) => {
    console.error(`[API Request Error]`, error)
    return Promise.reject(error)
  }
)

apiClient.interceptors.response.use(
  (response) => {
    console.log(`[API Request Completed] ${response.config.method?.toUpperCase()} ${response.config.url} - Status: ${response.status}`)
    return response
  },
  (error) => {
    if (axios.isCancel(error)) {
      console.error(`[API Request Cancelled] ${error.message}`)
    } else if (error.code === 'ECONNABORTED') {
      console.error(`[API Request Timeout] The request exceeded the 5-minute timeout.`)
    } else {
      if (error.response?.status !== 404) {
        console.error(`[API Request Failed] Status: ${error.response?.status || 'Unknown'} - ${error.message}`)
      }
    }
    return Promise.reject(error)
  }
)
