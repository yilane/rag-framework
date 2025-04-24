import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'Layout',
      component: () => import('../views/layout/index.vue'),
      redirect: '/load-file',
      children: [
        {
          path: 'load-file',
          name: 'LoadFile',
          component: () => import('../views/load-file/index.vue'),
          meta: {
            title: '加载文档',
            icon: 'Upload'
          }
        },
        {
          path: 'chunk-file',
          name: 'ChunkFile',
          component: () => import('../views/chunk-file/index.vue'),
          meta: {
            title: '分割文档',
            icon: 'Document'
          }
        },
        {
          path: 'parse-file',
          name: 'ParseFile',
          component: () => import('../views/parse-file/index.vue'),
          meta: {
            title: '解析文档',
            icon: 'Document'
          }
        },
        {
          path: 'embedding',
          name: 'Embedding',
          component: () => import('../views/embedding/index.vue'),
          meta: {
            title: '嵌入文档',
            icon: 'Connection'
          }
        },
        {
          path: 'indexing',
          name: 'Indexing',
          component: () => import('../views/indexing/index.vue'),
          meta: {
            title: '向量数据索引',
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