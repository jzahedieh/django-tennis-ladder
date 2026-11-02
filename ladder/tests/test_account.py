import datetime
from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from ladder.models import Season, Ladder, League, Player


class AccountViewTests(TestCase):
    def setUp(self):
        self.season = Season.objects.create(
            name='2026 Round 1',
            start_date=datetime.date(2026, 1, 1),
            end_date=datetime.date(2026, 12, 31),
            season_round=1,
            is_draft=False,
        )
        self.ladder = Ladder.objects.create(
            season=self.season,
            division=1,
            ladder_type='Singles',
        )
        self.user = User.objects.create_user(
            username='roger@example.com',
            email='roger@example.com',
            password='oldpassword123',
            first_name='Roger',
            last_name='Federer',
        )
        self.player = Player.objects.create(
            first_name='Roger',
            last_name='Federer',
            user=self.user,
        )
        self.league = League.objects.create(
            ladder=self.ladder,
            player=self.player,
            sort_order=10,
        )

    def test_account_requires_login(self):
        response = self.client.get(reverse('account'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_account_renders_player_and_ladder_details(self):
        self.client.login(username='roger@example.com', password='oldpassword123')
        response = self.client.get(reverse('account'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'My Account')
        self.assertContains(response, 'Roger Federer')
        self.assertContains(response, 'roger@example.com')
        self.assertContains(response, 'Division 1')
        self.assertContains(response, reverse('player_history', args=[self.player.id]))
        self.assertNotContains(response, 'autofocus')

    def test_account_email_change_success(self):
        self.client.login(username='roger@example.com', password='oldpassword123')
        response = self.client.post(reverse('account'), {
            'action': 'update_email',
            'email': '  Roger.New@Example.com  ',
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Your email address has been updated successfully.')
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'roger.new@example.com')
        self.assertEqual(self.user.username, 'roger.new@example.com')

        # Verify notification email sent to both old and new addresses
        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.to, ['roger@example.com', 'roger.new@example.com'])
        self.assertIn('roger@example.com', sent_email.body)
        self.assertIn('roger.new@example.com', sent_email.body)
        self.assertIn('feedback@highgate-ladder.co.uk', sent_email.body)

        # Verify user can log in with the new email address
        self.client.logout()
        self.assertTrue(self.client.login(username='roger.new@example.com', password='oldpassword123'))

    def test_account_email_change_rejects_duplicate_and_invalid_email(self):
        User.objects.create_user(
            username='rafa@example.com',
            email='rafa@example.com',
            password='password123',
        )
        self.client.login(username='roger@example.com', password='oldpassword123')

        dup_resp = self.client.post(reverse('account'), {
            'action': 'update_email',
            'email': 'RAFA@example.com',
        })
        self.assertEqual(dup_resp.status_code, 200)
        self.assertContains(dup_resp, 'This email address is already in use by another account.')
        self.assertContains(dup_resp, 'is-invalid')
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'roger@example.com')

        invalid_resp = self.client.post(reverse('account'), {
            'action': 'update_email',
            'email': 'not-an-email',
        })
        self.assertEqual(invalid_resp.status_code, 200)
        self.assertContains(invalid_resp, 'is-invalid')
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'roger@example.com')

    def test_navbar_shows_login_when_anonymous_and_full_name_dropdown_when_authenticated(self):
        anon_resp = self.client.get(reverse('index'))
        self.assertContains(anon_resp, 'Log In')
        self.assertNotContains(anon_resp, 'userAccountDropdown')

        self.client.login(username='roger@example.com', password='oldpassword123')
        auth_resp = self.client.get(reverse('index'))
        self.assertContains(auth_resp, 'userAccountDropdown')
        self.assertContains(auth_resp, 'Roger Federer')
        self.assertContains(auth_resp, reverse('account'))
        self.assertContains(auth_resp, reverse('player_history', args=[self.player.id]))

    def test_account_password_change_success(self):
        self.client.login(username='roger@example.com', password='oldpassword123')
        response = self.client.post(reverse('account'), {
            'old_password': 'oldpassword123',
            'new_password1': 'NewStrongPass99!',
            'new_password2': 'NewStrongPass99!',
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Your password has been updated successfully.')
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewStrongPass99!'))

    def test_account_password_change_invalid(self):
        self.client.login(username='roger@example.com', password='oldpassword123')
        response = self.client.post(reverse('account'), {
            'old_password': 'wrongpassword',
            'new_password1': 'NewStrongPass99!',
            'new_password2': 'NewStrongPass99!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'is-invalid')
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('oldpassword123'))

    def test_result_entry_renders_opponent_cards_and_score_picker(self):
        opponent = Player.objects.create(first_name='Rafael', last_name='Nadal')
        League.objects.create(ladder=self.ladder, player=opponent, sort_order=20)

        self.client.login(username='roger@example.com', password='oldpassword123')
        response = self.client.get(reverse('result_entry'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Rafael Nadal')
        self.assertContains(response, reverse('player_history', args=[opponent.id]))
        self.assertContains(response, reverse('head_to_head', args=[self.player.id, opponent.id]))
        self.assertContains(response, 'score-picker-grid')
        self.assertContains(response, 'h2hLightboxModal')

