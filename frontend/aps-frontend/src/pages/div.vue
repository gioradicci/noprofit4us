<script setup lang="ts">
defineProps<{
	search: string;
}>()
</script>

<template>
	<FloatLabel variant="on">
	      <InputText
	        v-model="search"
	        id="search_input"
	       
	      />
	      <label for="search_input">Cerca nome o cognome...</label>
	    </FloatLabel>
</template>
