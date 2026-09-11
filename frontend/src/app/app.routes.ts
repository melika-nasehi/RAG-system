import { Routes } from '@angular/router';
import { adminGuard, authGuard, guestGuard } from './services/guards';

export const routes: Routes = [
  {
    path: '',
    canActivate: [authGuard],
    loadComponent: () => import('./pages/chat-page/chat-page').then((m) => m.ChatPage),
  },
  {
    path: 'login',
    canActivate: [guestGuard],
    loadComponent: () => import('./pages/login-page/login-page').then((m) => m.LoginPage),
  },
  {
    path: 'register',
    canActivate: [guestGuard],
    loadComponent: () =>
      import('./pages/register-page/register-page').then((m) => m.RegisterPage),
  },
  {
    path: 'admin/documents',
    canActivate: [adminGuard],
    loadComponent: () =>
      import('./pages/admin-documents-page/admin-documents-page').then(
        (m) => m.AdminDocumentsPage,
      ),
  },
  { path: '**', redirectTo: '' },
];
