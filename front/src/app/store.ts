import { configureStore, createListenerMiddleware } from '@reduxjs/toolkit'
import { useDispatch, useSelector } from 'react-redux'
import authReducer, {
  clearCredentials,
  setCredentials,
  setPasswordChangeRequired,
} from '../features/auth/redux/authSlice'
import {
  removeAuthSession,
  removePasswordChangeChallenge,
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
