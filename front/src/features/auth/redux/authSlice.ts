import { createSlice, type PayloadAction } from '@reduxjs/toolkit'
import { resolveActiveBranch } from '../branchAccess'
import {
  loadActiveBranch,
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
  status: 'checking' | 'authenticated' | 'unauthenticated'
  isAuthenticated: boolean
  user: AuthUser | null
  /** Sucursal en la que se está trabajando: todo lo que se carga y se lista es de esta sucursal. */
  activeBranchId: number | null
  passwordChangeChallenge: PasswordChangeChallenge | null
}

const storedSession = loadAuthSession()
const storedPasswordChangeChallenge = storedSession
  ? null
  : loadPasswordChangeChallenge()

const initialState: AuthState = {
  token: storedSession?.token ?? null,
  status: storedSession ? 'checking' : 'unauthenticated',
  isAuthenticated: false,
  user: storedSession?.user ?? null,
  activeBranchId: storedSession
    ? resolveActiveBranch(storedSession.user.branches, loadActiveBranch(storedSession.user.id))
    : null,
  passwordChangeChallenge: storedPasswordChangeChallenge,
}

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    setCredentials: (state, action: PayloadAction<AuthSession>) => {
      state.token = action.payload.token
      state.status = 'authenticated'
      state.isAuthenticated = true
      state.user = action.payload.user
      state.activeBranchId = resolveActiveBranch(
        action.payload.user.branches,
        state.activeBranchId ?? loadActiveBranch(action.payload.user.id),
      )
      state.passwordChangeChallenge = null
    },
    setActiveBranch: (state, action: PayloadAction<number>) => {
      if (state.user?.branches.some((branch) => branch.id === action.payload)) {
        state.activeBranchId = action.payload
      }
    },
    setPasswordChangeRequired: (
      state,
      action: PayloadAction<PasswordChangeChallenge>,
    ) => {
      state.token = null
      state.status = 'unauthenticated'
      state.isAuthenticated = false
      state.user = null
      state.activeBranchId = null
      state.passwordChangeChallenge = action.payload
    },
    clearCredentials: (state) => {
      state.token = null
      state.status = 'unauthenticated'
      state.isAuthenticated = false
      state.user = null
      state.activeBranchId = null
      state.passwordChangeChallenge = null
    },
  },
  selectors: {
    selectAuthToken: (state) => state.token,
    selectAuthStatus: (state) => state.status,
    selectCurrentUser: (state) => state.user,
    selectIsAuthenticated: (state) => state.isAuthenticated,
    selectPasswordChangeChallenge: (state) => state.passwordChangeChallenge,
    selectActiveBranchId: (state) => state.activeBranchId,
    selectActiveBranch: (state) =>
      state.user?.branches.find((branch) => branch.id === state.activeBranchId) ?? null,
  },
})

export const {
  clearCredentials,
  setActiveBranch,
  setCredentials,
  setPasswordChangeRequired,
} = authSlice.actions
export const {
  selectAuthToken,
  selectAuthStatus,
  selectCurrentUser,
  selectIsAuthenticated,
  selectPasswordChangeChallenge,
  selectActiveBranchId,
  selectActiveBranch,
} = authSlice.selectors
export default authSlice.reducer
