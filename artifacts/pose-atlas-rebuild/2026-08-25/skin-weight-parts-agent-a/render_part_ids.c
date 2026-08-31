#include "ufbx.h"
#include <float.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define WIDTH 1024
#define HEIGHT 1536
#define PI 3.14159265358979323846
typedef struct vec3 { double x,y,z; } vec3;
typedef struct tri { uint32_t a,b,c; } tri;

static int load_vertices(const char *path, vec3 **vertices, uint32_t *count)
{
    FILE *file=NULL; char magic[8]; uint32_t dimensions;
    if (fopen_s(&file,path,"rb") != 0 || !file) return 0;
    if (fread(magic,1,8,file)!=8 || memcmp(magic,"MHRVTX2\0",8)!=0 || fread(count,4,1,file)!=1 || fread(&dimensions,4,1,file)!=1 || dimensions!=3) { fclose(file); return 0; }
    *vertices=(vec3*)malloc((size_t)*count*sizeof(vec3));
    if(!*vertices || fread(*vertices,sizeof(vec3),*count,file)!=*count){free(*vertices);fclose(file);return 0;}
    fclose(file); return 1;
}
static int load_faces(const char *fbx,uint32_t vertex_count,tri **faces,uint32_t *count)
{
    ufbx_error error; ufbx_load_opts opts={0}; ufbx_scene *scene=ufbx_load_file(fbx,&opts,&error); size_t i;
    if(!scene || scene->meshes.count!=1){if(scene)ufbx_free_scene(scene);return 0;}
    const ufbx_mesh *mesh=scene->meshes.data[0]; if(mesh->num_faces!=36874 || mesh->num_vertices!=vertex_count){ufbx_free_scene(scene);return 0;}
    *faces=(tri*)malloc(mesh->num_faces*sizeof(tri)); if(!*faces){ufbx_free_scene(scene);return 0;}
    for(i=0;i<mesh->faces.count;i++){ufbx_face f=mesh->faces.data[i]; if(f.num_indices!=3){free(*faces);ufbx_free_scene(scene);return 0;} (*faces)[i]=(tri){mesh->vertex_indices.data[f.index_begin],mesh->vertex_indices.data[f.index_begin+1],mesh->vertex_indices.data[f.index_begin+2]};}
    *count=(uint32_t)mesh->num_faces; ufbx_free_scene(scene); return 1;
}
static int load_face_parts(const char *path,uint8_t **parts,uint32_t expected)
{
    FILE *file=NULL; char line[128]; unsigned index,part; uint32_t count=0;
    if(fopen_s(&file,path,"rb")!=0||!file)return 0; if(!fgets(line,sizeof(line),file)){fclose(file);return 0;}
    *parts=(uint8_t*)malloc(expected); if(!*parts){fclose(file);return 0;}
    while(fgets(line,sizeof(line),file)){if(sscanf_s(line,"%u\t%u",&index,&part)!=2||index!=count||part>255||count>=expected){free(*parts);fclose(file);return 0;}(*parts)[count++]=(uint8_t)part;}
    fclose(file); return count==expected;
}
static double edge(double ax,double ay,double bx,double by,double px,double py){return(px-ax)*(by-ay)-(py-ay)*(bx-ax);}
static int write_pgm(const char *path,const uint8_t *data){FILE *f=NULL;if(fopen_s(&f,path,"wb")!=0||!f)return 0;fprintf(f,"P5\n%d %d\n255\n",WIDTH,HEIGHT);int ok=fwrite(data,1,(size_t)WIDTH*HEIGHT,f)==(size_t)WIDTH*HEIGHT;fclose(f);return ok;}
int main(int argc,char **argv)
{
    vec3 *base=NULL,*rotated=NULL; tri *faces=NULL; uint8_t *face_parts=NULL,*pixels=NULL; double *sx=NULL,*sy=NULL,*zb=NULL; uint32_t nv=0,nf=0,i; int view;
    const int yaws[24]={-180,-165,-150,-135,-120,-105,-90,-75,-60,-45,-30,-15,0,15,30,45,60,75,90,105,120,135,150,165};
    if(argc!=5){fputs("usage: render_part_ids vertices.bin lod1.fbx face-parts.tsv output_dir\n",stderr);return 2;}
    if(!load_vertices(argv[1],&base,&nv)||nv!=18439)return 3; if(!load_faces(argv[2],nv,&faces,&nf))return 4; if(!load_face_parts(argv[3],&face_parts,nf))return 5;
    double ymin=DBL_MAX,ymax=-DBL_MAX,rmax=0; for(i=0;i<nv;i++){double r=sqrt(base[i].x*base[i].x+base[i].z*base[i].z);if(base[i].y<ymin)ymin=base[i].y;if(base[i].y>ymax)ymax=base[i].y;if(r>rmax)rmax=r;}
    const double margin=24.0,sxscale=(WIDTH-2*margin)/(2*rmax),syscale=(HEIGHT-2*margin)/(ymax-ymin),scale=sxscale<syscale?sxscale:syscale,ycenter=.5*(ymin+ymax);
    rotated=(vec3*)malloc((size_t)nv*sizeof(vec3));sx=(double*)malloc((size_t)nv*sizeof(double));sy=(double*)malloc((size_t)nv*sizeof(double));zb=(double*)malloc((size_t)WIDTH*HEIGHT*sizeof(double));pixels=(uint8_t*)malloc((size_t)WIDTH*HEIGHT);if(!rotated||!sx||!sy||!zb||!pixels)return 6;
    for(view=0;view<24;view++){double rad=yaws[view]*PI/180.0,co=cos(rad),si=sin(rad);size_t p;char path[2048],id[64];
        for(i=0;i<nv;i++){rotated[i]=(vec3){co*base[i].x+si*base[i].z,base[i].y,-si*base[i].x+co*base[i].z};sx[i]=WIDTH*.5+rotated[i].x*scale;sy[i]=HEIGHT*.5-(rotated[i].y-ycenter)*scale;}
        for(p=0;p<(size_t)WIDTH*HEIGHT;p++){zb[p]=-DBL_MAX;pixels[p]=0;}
        for(i=0;i<nf;i++){tri f=faces[i];double ax=sx[f.a],ay=sy[f.a],bx=sx[f.b],by=sy[f.b],cx=sx[f.c],cy=sy[f.c],area=edge(ax,ay,bx,by,cx,cy);int x,y,minx,maxx,miny,maxy;if(fabs(area)<1e-12)continue;minx=(int)floor(fmin(ax,fmin(bx,cx)));maxx=(int)ceil(fmax(ax,fmax(bx,cx)));miny=(int)floor(fmin(ay,fmin(by,cy)));maxy=(int)ceil(fmax(ay,fmax(by,cy)));if(minx<0)minx=0;if(maxx>=WIDTH)maxx=WIDTH-1;if(miny<0)miny=0;if(maxy>=HEIGHT)maxy=HEIGHT-1;
            for(y=miny;y<=maxy;y++)for(x=minx;x<=maxx;x++){double px=x+.5,py=y+.5,wa=edge(bx,by,cx,cy,px,py)/area,wb=edge(cx,cy,ax,ay,px,py)/area,wc=edge(ax,ay,bx,by,px,py)/area,z;size_t q;if(wa<0||wb<0||wc<0)continue;z=wa*rotated[f.a].z+wb*rotated[f.b].z+wc*rotated[f.c].z;q=(size_t)y*WIDTH+x;if(z<=zb[q])continue;zb[q]=z;pixels[q]=face_parts[i];}}
        snprintf(id,sizeof(id),"yaw%+04d-pitch+00",yaws[view]);snprintf(path,sizeof(path),"%s\\%s_part-id.pgm",argv[4],id);if(!write_pgm(path,pixels))return 7;
    }
    printf("{\"status\":\"PASS\",\"views\":24,\"width\":1024,\"height\":1536,\"vertices\":%u,\"faces\":%u,\"scale\":%.17g}\n",nv,nf,scale);
    free(pixels);free(zb);free(sy);free(sx);free(rotated);free(face_parts);free(faces);free(base);return 0;
}
