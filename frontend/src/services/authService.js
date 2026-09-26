import api from './api';

export const authService = {
  login: async (usernameOrEmail, password) => {
    return await api.post('/auth/login', {
      username: usernameOrEmail,
      password,
    });
  },

  signup: async (username, email, password, role = 'USER') => {
    return await api.post('/auth/signup', { username, email, password, role });
  },

  getMe: async () => {
    return await api.get('/auth/me');
  },
};

export default authService;
