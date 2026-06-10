import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/dashboard' },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
  },
  {
    path: '/',
    component: () => import('../views/Dashboard.vue'),
    meta: { requiresAuth: true },
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'DashboardHome',
        component: () => import('../views/DashboardHome.vue'),
      },
      {
        path: 'clubs',
        name: 'Clubs',
        component: () => import('../views/Clubs.vue'),
      },
      {
        path: 'clubs/:id',
        name: 'ClubDetail',
        component: () => import('../views/ClubDetail.vue'),
      },
      {
        path: 'activities',
        name: 'Activities',
        component: () => import('../views/Activities.vue'),
      },
      {
        path: 'activities/:id',
        name: 'ActivityDetail',
        component: () => import('../views/ActivityDetail.vue'),
      },
      {
        path: 'notifications',
        name: 'Notifications',
        component: () => import('../views/Notifications.vue'),
      },
      {
        path: 'admin-approval',
        name: 'AdminApproval',
        component: () => import('../views/AdminApproval.vue'),
      },
      {
        path: 'ai-recommend',
        name: 'AIRecommend',
        component: () => import('../views/AIRecommend.vue'),
      },
      {
        path: 'checkin',
        name: 'Checkin',
        component: () => import('../views/Checkin.vue'),
      },
    ],
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  if (to.meta.requiresAuth && !token) {
    next('/login')
  } else {
    next()
  }
})

export default router
