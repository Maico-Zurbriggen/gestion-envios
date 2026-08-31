import { createSlice, type PayloadAction } from '@reduxjs/toolkit'
import { loadAuthSession } from '../services/authStorage'
import type { AuthSession, AuthUser } from '../types/auth.types'

interface AuthState {
  token: string | null
  isAuthenticated: boolean
  user: AuthUser | null
}

const storedSession = loadAuthSession()

const initialState: AuthState = {
  token: storedSession?.token ?? null,
  isAuthenticated: Boolean(storedSession),
  user: storedSession?.user ?? null,
}

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    setCredentials: (state, action: PayloadAction<AuthSession>) => {
      state.token = action.payload.token
      state.isAuthenticated = true
      state.user = action.payload.user
    },
    clearCredentials: (state) => {
      state.token = null
      state.isAuthenticated = false
      state.user = null
    },
  },
  selectors: {
    selectAuthToken: (state) => state.token,
    selectCurrentUser: (state) => state.user,
    selectIsAuthenticated: (state) => state.isAuthenticated,
  },
})

export const { clearCredentials, setCredentials } = authSlice.actions
export const {
  selectAuthToken,
  selectCurrentUser,
  selectIsAuthenticated,
} = authSlice.selectors
export default authSlice.reducer
