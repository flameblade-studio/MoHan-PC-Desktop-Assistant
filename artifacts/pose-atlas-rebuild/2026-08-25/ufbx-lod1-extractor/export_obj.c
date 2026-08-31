#include <stdio.h>
#include <stdlib.h>

#include "ufbx.h"

int main(int argc, char **argv)
{
    if (argc != 3) {
        fprintf(stderr, "usage: export_obj <input.fbx> <output.obj>\n");
        return 2;
    }

    ufbx_load_opts opts = { 0 };
    ufbx_error error;
    ufbx_scene *scene = ufbx_load_file(argv[1], &opts, &error);
    if (!scene) {
        fprintf(stderr, "ufbx_load_file failed: %s\n", error.description.data);
        return 1;
    }
    if (scene->meshes.count != 1) {
        fprintf(stderr, "expected exactly one mesh, got %zu\n", scene->meshes.count);
        ufbx_free_scene(scene);
        return 1;
    }

    const ufbx_mesh *mesh = scene->meshes.data[0];
    FILE *out = fopen(argv[2], "wb");
    if (!out) {
        fprintf(stderr, "failed to open output\n");
        ufbx_free_scene(scene);
        return 1;
    }

    fprintf(out, "# MHR LOD1 base topology extracted with ufbx v0.23.0 (MIT)\n");
    fprintf(out, "o mhr_lod1\n");
    for (size_t i = 0; i < mesh->vertices.count; ++i) {
        ufbx_vec3 v = mesh->vertices.data[i];
        fprintf(out, "v %.17g %.17g %.17g\n", v.x, v.y, v.z);
    }

    size_t triangle_count = 0;
    uint32_t *tri_indices = (uint32_t *)malloc(mesh->max_face_triangles * 3 * sizeof(uint32_t));
    if (!tri_indices) {
        fprintf(stderr, "allocation failed\n");
        fclose(out);
        ufbx_free_scene(scene);
        return 1;
    }
    for (size_t face_ix = 0; face_ix < mesh->faces.count; ++face_ix) {
        ufbx_face face = mesh->faces.data[face_ix];
        size_t num_triangles = ufbx_triangulate_face(
            tri_indices,
            mesh->max_face_triangles * 3,
            mesh,
            face
        );
        for (size_t tri_ix = 0; tri_ix < num_triangles; ++tri_ix) {
            size_t ia = tri_indices[tri_ix * 3 + 0];
            size_t ib = tri_indices[tri_ix * 3 + 1];
            size_t ic = tri_indices[tri_ix * 3 + 2];
            uint32_t a = mesh->vertex_indices.data[ia] + 1;
            uint32_t b = mesh->vertex_indices.data[ib] + 1;
            uint32_t c = mesh->vertex_indices.data[ic] + 1;
            fprintf(out, "f %u %u %u\n", a, b, c);
            triangle_count++;
        }
    }

    free(tri_indices);
    fclose(out);
    printf("vertices=%zu triangles=%zu output=%s\n", mesh->vertices.count, triangle_count, argv[2]);
    ufbx_free_scene(scene);
    return triangle_count == mesh->num_triangles ? 0 : 1;
}
