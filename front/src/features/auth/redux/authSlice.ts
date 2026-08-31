import { createSlice, type PayloadAction } from '@reduxjs/toolkit'

export type UserRole = 'admin' | 'operator' | 'viewer'

export interface AuthUser {
  id: string
  name: string
  roles: UserRole[]
}

interface AuthState {
  isAuthenticated: boolean
  user: AuthUser | null
}

const initialState: AuthState = {
  isAuthenticated: false,
  user: null,
}

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    setCredentials: (state, action: PayloadAction<AuthUser>) => {
      state.isAuthenticated = true
      state.user = action.payload
    },
    clearCredentials: (state) => {
      state.isAuthenticated = false
      state.user = null
    },
  },
  selectors: {
    selectCurrentUser: (state) => state.user,
    selectIsAuthenticated: (state) => state.isAuthenticated,
  },
})

export const { clearCredentials, setCredentials } = authSlice.actions
export const { selectCurrentUser, selectIsAuthenticated } = authSlice.selectors
export default authSlice.reducer
