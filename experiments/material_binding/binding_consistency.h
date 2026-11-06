/* The engine may edit a private material in place. Pointer identity is not
 * proof that its normal texture still belongs to the suit. GUI thread only. */
static unsigned long long binding_checks,binding_repairs;

static int repair_private_normal(void* material) {
 unsigned short techniques=og.tech_count(material);
 if(!techniques||techniques>16)return fail("Private material technique bound");
 unsigned main_passes=0,normals=0;void* normal_unit=NULL;
 for(unsigned short ti=0;ti<techniques;ti++){
  void* technique=og.tech_get(material,ti);if(!technique)return fail("Private technique missing");
  unsigned short passes=og.pass_count(technique);
  if(!passes||passes>16)return fail("Private material pass bound");
  for(unsigned short pi=0;pi<passes;pi++){
   void* pass=og.pass_get(technique,pi);if(!pass)return fail("Private pass missing");
   const Str32* program=og.pass_fp(pass);
   if(!equal(program,PROGRAM)&&!equal(program,DAY_PROGRAM))continue;
   if(!equal(program,night_mode?PROGRAM:DAY_PROGRAM))return fail("Private main program differs from day/night state");
   main_passes++;
   unsigned short units=og.unit_count(pass);
   if(!units||units>64)return fail("Private texture unit bound");
   for(unsigned short ui=0;ui<units;ui++){
    void* unit=og.unit_get(pass,ui);if(!unit)return fail("Private texture unit missing");
    if(equal(og.unit_name(unit),"normalMap")){normal_unit=unit;normals++;}
   }
  }
 }
 if(main_passes!=1||normals!=1)return fail("Expected one private main pass and normalMap");
 binding_checks++;
 if(equal(og.unit_texture(normal_unit),NORMAL))return 0;
 Str32 normal=str(NORMAL);og.unit_set_texture(normal_unit,&normal,2);
 if(!equal(og.unit_texture(normal_unit),NORMAL))return fail("Private normal binding readback failed");
 binding_repairs++;
 return 1;
}

API int T60_material_binding_status(char* output,size_t capacity) {
 if(!output||capacity<256)return -1;
 return snprintf(output,capacity,
  "{\"checks\":%llu,\"repairs\":%llu,\"slots\":%d,\"limit\":32,\"enabled\":%d}",
  binding_checks,binding_repairs,state.slots,state.enabled);
}
