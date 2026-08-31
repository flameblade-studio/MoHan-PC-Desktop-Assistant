#include <stdio.h>
#include <stdlib.h>

#include "ufbx.h"

int main(int argc, char **argv)
{
    if (argc != 2) {
        fprintf(stderr, "usage: list_meshes <input.fbx>\n");
        return 2;
    }

    ufbx_load_opts opts = { 0 };
    ufbx_error error;
    ufbx_scene *scene = ufbx_load_file(argv[1], &opts, &error);
    if (!scene) {
        fprintf(stderr, "ufbx_load_file failed: %s\n", error.description.data);
        return 1;
    }

    printf("scene_meshes=%zu\n", scene->meshes.count);
    for (size_t i = 0; i < scene->meshes.count; ++i) {
        const ufbx_mesh *mesh = scene->meshes.data[i];
        printf(
            "mesh[%zu] name=%.*s num_vertices=%zu num_indices=%zu faces=%zu triangles=%zu instances=%zu\n",
            i,
            (int)mesh->name.length,
            mesh->name.data,
            mesh->num_vertices,
            mesh->num_indices,
            mesh->faces.count,
            mesh->num_triangles,
            mesh->instances.count
        );
    }

    ufbx_free_scene(scene);
    return 0;
}
