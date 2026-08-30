#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "ufbx.h"

static void print_json_string(ufbx_string value)
{
    putchar('"');
    for (size_t i = 0; i < value.length; ++i) {
        unsigned char c = (unsigned char)value.data[i];
        if (c == '"' || c == '\\') putchar('\\');
        if (c >= 0x20) putchar((int)c);
    }
    putchar('"');
}

int main(int argc, char **argv)
{
    if (argc != 3) return 2;
    ufbx_error error;
    ufbx_load_opts opts = {0};
    ufbx_scene *scene = ufbx_load_file(argv[1], &opts, &error);
    if (!scene) return 3;
    if (scene->meshes.count != 1) { ufbx_free_scene(scene); return 4; }
    ufbx_mesh *mesh = scene->meshes.data[0];
    if (mesh->skin_deformers.count != 1) { ufbx_free_scene(scene); return 5; }
    ufbx_skin_deformer *skin = mesh->skin_deformers.data[0];
    if (skin->clusters.count != 127) { ufbx_free_scene(scene); return 6; }
    FILE *out = NULL;
    if (fopen_s(&out, argv[2], "wb") != 0 || !out) { ufbx_free_scene(scene); return 7; }
    fprintf(out, "cluster_index\tbone_name\tparent_name\tx\ty\tz\tweight_count\n");
    for (size_t i = 0; i < skin->clusters.count; ++i) {
        ufbx_skin_cluster *cluster = skin->clusters.data[i];
        ufbx_node *bone = cluster->bone_node;
        if (!bone) { fclose(out); ufbx_free_scene(scene); return 8; }
        const char *parent = bone->parent ? bone->parent->name.data : "";
        fprintf(out, "%zu\t%.*s\t%s\t%.17g\t%.17g\t%.17g\t%zu\n",
            i, (int)bone->name.length, bone->name.data, parent,
            (double)bone->node_to_world.m03,
            (double)bone->node_to_world.m13,
            (double)bone->node_to_world.m23,
            cluster->num_weights);
    }
    fclose(out);
    printf("{");
    printf("\"status\":\"PASS\",\"clusters\":%zu,\"mesh_vertices\":%zu,\"output\":", skin->clusters.count, mesh->num_vertices);
    ufbx_string output = { argv[2], strlen(argv[2]) };
    print_json_string(output);
    printf("}\n");
    ufbx_free_scene(scene);
    return 0;
}
