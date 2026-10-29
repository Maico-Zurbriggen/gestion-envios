import { configureStore, createListenerMiddleware } from '@reduxjs/toolkit'
import { useDispatch, useSelector } from 'react-redux'
import authReducer, {
  clearCredentials,
  setActiveBranch,
  setCredentials,
  setPasswordChangeRequired,
} from '../features/auth/redux/authSlice'
import {
  removeAuthSession,
  removePasswordChangeChallenge,
  saveActiveBranch,
  saveAuthSession,
  savePasswordChangeChallenge,
} from '../features/auth/services/authStorage'

const authListener = createListenerMiddleware()

authListener.startListening({
  actionCreator: setCredentials,
  effect: (action) => {
    saveAuthSession(action.payload)
    removePasswordChangeChallenge()
  },
})

// Se recuerda la última sucursal de cada usuario.
authListener.startListening({
  predicate: (action) => setCredentials.match(action) || setActiveBranch.match(action),
  effect: (_action, api) => {
    const { user, activeBranchId } = (api.getState() as { auth: { user: { id: string } | null; activeBranchId: number | null } }).auth
    if (user && activeBranchId !== null) saveActiveBranch(user.id, activeBranchId)
  },
})

authListener.startListening({
  actionCreator: setPasswordChangeRequired,
  effect: (action) => {
    removeAuthSession()
    savePasswordChangeChallenge(action.payload)
  },
})

authListener.startListening({
  actionCreator: clearCredentials,
  effect: () => {
    removeAuthSession()
    removePasswordChangeChallenge()
  },
})

export const store = configureStore({
  reducer: {
    auth: authReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware().prepend(authListener.middleware),
})

export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch

export const useAppDispatch = useDispatch.withTypes<AppDispatch>()
export const useAppSelector = useSelector.withTypes<RootState>()
