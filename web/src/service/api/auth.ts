import { request } from '../request';

/**
 * login
 *
 * @param userName user name
 * @param password password
 */
export function fetchLogin(userName: string, password: string) {
  return request<Api.Auth.LoginToken>({
    url: '/auth/login',
    method: 'post',
    data: {
      userName,
      password
    }
  });
}

/** get user info */
export function fetchGetUserInfo() {
  return request<Api.Auth.UserInfo>({ url: '/auth/user-info' });
}

/**
 * refresh token
 *
 * @param refreshToken refresh token
 */
export function fetchRefreshToken(refreshToken: string) {
  return request<Api.Auth.LoginToken>({
    url: '/auth/refresh-token',
    method: 'post',
    data: {
      refreshToken
    }
  });
}

/**
 * return custom backend error
 *
 * @param code error code
 * @param msg error message
 */
export function fetchCustomBackendError(code: string, msg: string) {
  return request({ url: '/auth/error', params: { code, msg } });
}

/**
 * register user
 *
 * @param userName user name
 * @param password password
 * @param userEmail email (optional)
 * @param userPhone phone (optional)
 * @param nickName nick name (optional)
 * @param userGender gender (optional)
 */
export function fetchRegister(
  userName: string,
  password: string,
  userEmail?: string,
  userPhone?: string,
  nickName?: string,
  userGender?: string
) {
  return request({
    url: '/auth/register',
    method: 'post',
    data: {
      userName,
      password,
      userEmail,
      userPhone,
      nickName,
      userGender
    }
  });
}

/**
 * send reset code
 *
 * @param email user email
 */
export function fetchSendResetCode(email: string) {
  return request({
    url: '/auth/send-reset-code',
    method: 'post',
    data: {
      email
    }
  });
}

/**
 * reset password
 *
 * @param email user email
 * @param code verification code
 * @param newPassword new password
 */
export function fetchResetPassword(email: string, code: string, newPassword: string) {
  return request({
    url: '/auth/reset-password',
    method: 'post',
    data: {
      email,
      code,
      new_password: newPassword
    }
  });
}

/**
 * update password
 *
 * @param oldPassword old password
 * @param newPassword new password
 */
export function fetchUpdatePassword(oldPassword: string, newPassword: string) {
  return request({
    url: '/auth/update-password',
    method: 'post',
    data: {
      oldPassword,
      newPassword
    }
  });
}
