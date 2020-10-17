<template>
  <v-app>
    <v-navigation-drawer v-model="drawer" fixed app>
      <v-list>
        <v-list-item
          v-for="(item, i) in items"
          :key="i"
          :to="item.to"
          router
          exact
        >
          <v-list-item-action>
            <v-icon>{{ item.icon }}</v-icon>
          </v-list-item-action>
          <v-list-item-content>
            <v-list-item-title v-text="item.title" />
          </v-list-item-content>
        </v-list-item>
      </v-list>
    </v-navigation-drawer>
    <v-app-bar fixed app>
      <v-app-bar-nav-icon @click.stop="drawer = !drawer" />
      <v-toolbar-title v-text="title" />
      <v-spacer />
      <v-btn icon>
        <v-icon>mdi-account</v-icon>
      </v-btn>
    </v-app-bar>
    <v-main>
      <v-container>
        <nuxt />
      </v-container>
    </v-main>
    <v-footer padless>
      <v-col class="text-center" cols="12">
        <a href="mailto:feedback@highgate-ladder.co.uk" target="_top">
          feedback@highgate-ladder.co.uk
        </a>
      </v-col>
      <v-col class="text-center" cols="12">
        Want to contribute? <a href="https://github.com/jzahedieh/django-tennis-ladder" target="_blank">Github</a>
      </v-col>
    </v-footer>
  </v-app>
</template>

<script>
export default {
  data () {
    return {
      drawer: false,
      fixed: false,
      items: [
        {
          icon: 'mdi-tennis',
          title: 'Overview',
          to: '/'
        },
        {
          icon: 'mdi-tennis-ball',
          title: 'Season',
          to: '/inspire'
        },
        {
          icon: 'mdi-tennis-ball',
          title: 'Ladder',
          to: '/inspire'
        }
      ],
      title: 'Highgate Ladder Tracker'
    }
  }
}
</script>
