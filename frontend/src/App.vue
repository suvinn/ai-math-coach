<template>
  <div class="app">
    <header class="app-header">
      <RouterLink to="/home" class="logo">AI Math Coach</RouterLink>

      <nav class="nav">
        <RouterLink to="/home">홈</RouterLink>
        <RouterLink to="/history">학습 이력</RouterLink>
        <RouterLink to="/login">로그인</RouterLink>
      </nav>
    </header>

    <main class="app-main">
      <RouterView />
    </main>
  </div>
</template>