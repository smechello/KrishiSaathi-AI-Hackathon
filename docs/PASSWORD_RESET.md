# Password Reset Feature — Implementation Guide

## Overview

This document describes the password reset feature implementation for KrishiSaathi. When users forget their password, they can now request a password reset email from Supabase, click the link in the email, and be redirected to a dedicated page where they can set a new password.

## Architecture

### Components

1. **SupabaseManager Methods** (`backend/services/supabase_service.py`)
   - `reset_password(email)` - Sends password reset email (already existed)
   - `verify_recovery_token(access_token, refresh_token)` - NEW: Verifies recovery tokens and establishes session
   - `update_password(new_password)` - NEW: Updates the user's password using current session

2. **Reset Password Page** (`frontend/pages/Reset_Password.py`)
   - Dedicated page for handling password reset flow
   - Extracts recovery tokens from URL query parameters
   - Validates tokens and displays password reset form
   - Updates password and redirects to login page

## User Flow

1. **User requests password reset**
   - Goes to login page
   - Clicks "Reset Password" tab
   - Enters email address
   - Clicks "Send Reset Link"

2. **User receives email**
   - Supabase sends email with password reset link
   - Link format: `https://your-app.streamlit.app/?type=recovery&access_token=...&refresh_token=...`

3. **User clicks email link**
   - Browser opens the app with recovery tokens in URL
   - Streamlit detects query parameters
   - Redirects to Reset_Password page automatically (Streamlit's multi-page routing)

4. **User sets new password**
   - Reset_Password page verifies recovery tokens
   - Displays password reset form
   - User enters new password (twice for confirmation)
   - Submits form

5. **Password updated**
   - Supabase updates the password
   - Success message displayed
   - Automatic redirect to login page after 3 seconds
   - User can now sign in with new password

## Technical Details

### Query Parameters

When Supabase redirects from the password reset email, it includes these URL parameters:

- `type=recovery` - Indicates this is a password recovery request
- `access_token=<JWT>` - Temporary access token for the recovery session
- `refresh_token=<JWT>` - Refresh token for the recovery session

### Session Management

The recovery tokens establish a temporary session that allows the user to update their password. The session is:
- Created in `verify_recovery_token()` method
- Stored in Streamlit's session_state
- Used by `update_password()` to authenticate the password change request
- Cleared after successful password update

### Security

- Recovery tokens are time-limited (expire after a set period)
- Tokens can only be used once
- Password must meet minimum requirements (6 characters)
- Password confirmation required to prevent typos
- Session cleared after password update

## Configuration

### Supabase Dashboard Settings

1. **URL Configuration** (Authentication → URL Configuration)
   - Site URL: `https://krishisaathi-ai-hackathon.streamlit.app/`
   - Redirect URLs: Add your app URL(s)
     - Production: `https://krishisaathi-ai-hackathon.streamlit.app/`
     - Local dev: `http://localhost:8501/`

2. **Email Template** (Authentication → Email Templates → Recovery)
   - Default template works correctly
   - Uses `{{ .ConfirmationURL }}` which includes all recovery tokens
   - No changes needed to email template

### Environment Variables

No additional environment variables required. Uses existing:
- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_KEY` - Your Supabase anon/public key

## Testing

### Manual Testing Steps

1. **Test password reset request**
   ```
   1. Go to login page
   2. Click "Reset Password" tab
   3. Enter a valid user email
   4. Click "Send Reset Link"
   5. Verify success message appears
   ```

2. **Test email reception**
   ```
   1. Check inbox for password reset email
   2. Verify email contains reset link
   3. Verify link includes recovery tokens
   ```

3. **Test password reset page**
   ```
   1. Click link in email
   2. Verify redirect to Reset_Password page
   3. Verify user email is displayed
   4. Enter new password (min 6 chars)
   5. Confirm password (must match)
   6. Click "Update Password"
   7. Verify success message
   8. Verify automatic redirect to login
   ```

4. **Test with new password**
   ```
   1. Sign in with new password
   2. Verify login succeeds
   3. Verify access to app
   ```

### Error Cases to Test

- [ ] Expired recovery token (wait for expiration)
- [ ] Already-used recovery token (click link twice)
- [ ] Invalid recovery token (modify URL)
- [ ] Password too short (< 6 characters)
- [ ] Passwords don't match
- [ ] Empty password field
- [ ] Email for non-existent account

## Troubleshooting

### Issue: "Invalid or missing recovery link"

**Cause**: No recovery tokens in URL
**Solution**: User must click the link from their email, not navigate directly to the page

### Issue: "Recovery link verification failed"

**Cause**: Token expired or already used
**Solution**: Request a new password reset link

### Issue: "Failed to update password"

**Cause**: Various Supabase errors
**Solution**: Check Supabase logs, verify connection, request new reset link

### Issue: Page redirects to main page instead of Reset_Password

**Cause**: Incorrect redirect URL configuration in Supabase
**Solution**: 
1. Go to Supabase Dashboard → Authentication → URL Configuration
2. Verify Site URL matches your app URL
3. Verify app URL is in Redirect URLs list

## Files Modified

1. `backend/services/supabase_service.py` - Added `verify_recovery_token()` and `update_password()` methods
2. `frontend/pages/Reset_Password.py` - NEW: Password reset page
3. `docs/SUPABASE_SETUP.md` - Added password reset configuration section
4. `docs/USER_GUIDE.md` - Updated FAQ with password reset instructions
5. `docs/CHANGELOG.md` - Added entry for this fix

## Future Enhancements

Potential improvements:
- [ ] Add password strength indicator
- [ ] Add password requirements checklist
- [ ] Add "show password" toggle
- [ ] Add rate limiting for password reset requests
- [ ] Add email notification when password is changed
- [ ] Add password history (prevent reuse of recent passwords)
- [ ] Add 2FA/MFA support

## References

- [Supabase Auth Documentation](https://supabase.com/docs/guides/auth)
- [Supabase Password Reset](https://supabase.com/docs/guides/auth/auth-password-reset)
- [Streamlit Query Parameters](https://docs.streamlit.io/library/api-reference/utilities/st.query_params)
