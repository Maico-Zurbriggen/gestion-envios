import { createSlice, type PayloadAction } from '@reduxjs/toolkit'
import {
  loadAuthSession,
  loadPasswordChangeChallenge,
} from '../services/authStorage'
import type {
  AuthSession,
  AuthUser,
  PasswordChangeChallenge,
} from '../types/auth.types'

interface AuthState {
  token: string | null
  isAuthenticated: boolean
  user: AuthUser | null
  passwordChangeChallenge: PasswordChangeChallenge | null
}

const storedSession = loadAuthSession()
const storedPasswordChangeChallenge = storedSession
  ? null
  : loadPasswordChangeChallenge()

const initialState: AuthState = {
  token: storedSession?.token ?? null,
  isAuthenticated: Boolean(storedSession),
  user: storedSession?.user ?? null,
  passwordChangeChallenge: storedPasswordChangeChallenge,
}

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    setCredentials: (state, action: PayloadAction<AuthSession>) => {
      state.token = action.payload.token
      state.isAuthenticated = true
      state.user = action.payload.user
      state.passwordChangeChallenge = null
    },
    setPasswordChangeRequired: (
      state,
      action: PayloadAction<PasswordChangeChallenge>,
    ) => {
      state.token = null
      state.isAuthenticated = false
      state.user = null
      state.passwordChangeChallenge = action.payload
    },
    clearCredentials: (state) => {
      state.token = null
      state.isAuthenticated = false
      state.user = null
      state.passwordChangeChallenge = null
    },
  },
  selectors: {
    selectAuthToken: (state) => state.token,
    selectCurrentUser: (state) => state.user,
    selectIsAuthenticated: (state) => state.isAuthenticated,
    selectPasswordChangeChallenge: (state) => state.passwordChangeChallenge,
  },
})

export const {
  clearCredentials,
  setCredentials,
  setPasswordChangeRequired,
} = authSlice.actions
export const {
  selectAuthToken,
  selectCurrentUser,
  selectIsAuthenticated,
  selectPasswordChangeChallenge,
} = authSlice.selectors
export default authSlice.reducer
