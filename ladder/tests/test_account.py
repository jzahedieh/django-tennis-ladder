import datetime
from django.contrib.auth.models import User
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

