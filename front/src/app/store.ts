import { configureStore, createListenerMiddleware } from '@reduxjs/toolkit'
import { useDispatch, useSelector } from 'react-redux'
import authReducer, {
  clearCredentials,
  setCredentials,
} from '../features/auth/redux/authSlice'
import {
  removeAuthSession,
  saveAuthSession,
} from '../features/auth/services/authStorage'

const authListener = createListenerMiddleware()

authListener.startListening({
  actionCreator: setCredentials,
  effect: (action) => saveAuthSession(action.payload),
})

authListener.startListening({
  actionCreator: clearCredentials,
  effect: () => removeAuthSession(),
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
