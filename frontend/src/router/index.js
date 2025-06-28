import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'Layout',
      component: () => import('../views/layout/index.vue'),
      redirect: '/parse-file',
      children: [
        // {
        //   path: 'load-file',
        //   name: 'LoadFile',
        //   component: () => import('../views/load-file/index.vue'),
        //   meta: {
        //     title: '加载文档',
        //     icon: 'Upload'
        //   }
        // },
        {
          path: 'parse-file',
          name: 'ParseFile',
          component: () => import('../views/parse-file/index.vue'),
          meta: {
            title: '文档解析',
            icon: 'Document'
          }
        },
        {
          path: 'chunk-file',
          name: 'ChunkFile',
          component: () => import('../views/chunk-file/index.vue'),
          meta: {
            title: '文本分块',
            icon: 'Document'
          }
        },
        {
          path: 'embedding',
          name: 'Embedding',
          component: () => import('../views/embedding/index.vue'),
          meta: {
            title: '信息嵌入',
            icon: 'Connection'
          }
        },
        {
          path: 'indexing',
          name: 'Indexing',
          component: () => import('../views/indexing/index.vue'),
          meta: {
            title: '向量存储',
            icon: 'DataAnalysis'
          }
        },
        {
          path: 'search',
          name: 'Search',
          component: () => import('../views/search/index.vue'),
          meta: {
            title: '信息检索',
            icon: 'Search'
          }
        },
        {
          path: 'generation',
          name: 'Generation',
          component: () => import('../views/generation/index.vue'),
          meta: {
            title: '生成模型',
            icon: 'ChatSquare'
          }
        }
      ]
    }
  ]
})

export default router 