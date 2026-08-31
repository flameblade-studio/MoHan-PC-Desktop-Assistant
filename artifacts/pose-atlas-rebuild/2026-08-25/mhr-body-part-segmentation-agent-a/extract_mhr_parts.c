#include "ufbx.h"

#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define EXPECTED_VERTICES ((size_t)18439)
#define EXPECTED_FACES ((size_t)36874)

static const ufbx_mesh *find_mesh(const ufbx_scene *scene)
{
    const ufbx_mesh *result = NULL;
    size_t matches = 0, i;
    for (i = 0; i < scene->meshes.count; ++i) {
        const ufbx_mesh *mesh = scene->meshes.data[i];
        if (mesh->num_vertices == EXPECTED_VERTICES && mesh->num_faces == EXPECTED_FACES) {
            result = mesh;
            ++matches;
        }
    }
    return matches == 1 ? result : NULL;
}

static void print_name(FILE *file, ufbx_string name)
{
    size_t i;
    for (i = 0; i < name.length; ++i) {
        char c = name.data[i];
        fputc(c == '\t' || c == '\r' || c == '\n' ? ' ' : c, file);
    }
}

static int write_nodes(const char *path, const ufbx_mesh *mesh)
{
    FILE *file = fopen(path, "wb");
    size_t i;
    if (!file) return 0;
    fputs("instance_index\tnode_element_id\tnode_name\tmaterial_count\n", file);
    for (i = 0; i < mesh->instances.count; ++i) {
        const ufbx_node *node = mesh->instances.data[i];
        fprintf(file, "%zu\t%" PRIu32 "\t", i, node->element_id);
        print_name(file, node->name);
        fprintf(file, "\t%zu\n", node->materials.count);
    }
    return fclose(file) == 0;
}

static int write_materials(const char *path, const ufbx_mesh *mesh)
{
    FILE *file = fopen(path, "wb");
    size_t i;
    if (!file) return 0;
    fputs("material_index\tmaterial_element_id\tmaterial_name\tface_count\ttriangle_count\n", file);
    for (i = 0; i < mesh->materials.count; ++i) {
        const ufbx_material *material = mesh->materials.data[i];
        size_t faces = i < mesh->material_parts.count ? mesh->material_parts.data[i].num_faces : 0;
        size_t triangles = i < mesh->material_parts.count ? mesh->material_parts.data[i].num_triangles : 0;
        fprintf(file, "%zu\t%" PRIu32 "\t", i, material->element_id);
        print_name(file, material->name);
        fprintf(file, "\t%zu\t%zu\n", faces, triangles);
    }
    return fclose(file) == 0;
}

static int write_faces(const char *path, const ufbx_mesh *mesh)
{
    FILE *file = fopen(path, "wb");
    size_t i;
    if (!file) return 0;
    fputs("face_index\tmaterial_index\tface_group_index\n", file);
    for (i = 0; i < mesh->faces.count; ++i) {
        uint32_t material = mesh->face_material.count == mesh->faces.count ? mesh->face_material.data[i] : 0;
        uint32_t group = mesh->face_group.count == mesh->faces.count ? mesh->face_group.data[i] : UFBX_NO_INDEX;
        fprintf(file, "%zu\t%" PRIu32 "\t%" PRIu32 "\n", i, material, group);
    }
    return fclose(file) == 0;
}

static int write_groups(const char *path, const ufbx_mesh *mesh)
{
    FILE *file = fopen(path, "wb");
    size_t i;
    if (!file) return 0;
    fputs("face_group_index\tface_group_id\tface_group_name\tface_count\n", file);
    for (i = 0; i < mesh->face_groups.count; ++i) {
        ufbx_face_group group = mesh->face_groups.data[i];
        size_t faces = i < mesh->face_group_parts.count ? mesh->face_group_parts.data[i].num_faces : 0;
        fprintf(file, "%zu\t%d\t", i, group.id);
        print_name(file, group.name);
        fprintf(file, "\t%zu\n", faces);
    }
    return fclose(file) == 0;
}

int main(int argc, char **argv)
{
    ufbx_load_opts opts = {0};
    ufbx_error error;
    ufbx_scene *scene;
    const ufbx_mesh *mesh;
    char nodes[4096], materials[4096], faces[4096], groups[4096];
    if (argc != 3) {
        fputs("usage: extract_mhr_parts INPUT_FBX OUTPUT_PREFIX\n", stderr);
        return 2;
    }
    if (UFBX_HEADER_VERSION != ufbx_pack_version(0, 23, 0)) return 3;
    if (snprintf(nodes, sizeof(nodes), "%s.nodes.tsv", argv[2]) < 0 ||
        snprintf(materials, sizeof(materials), "%s.materials.tsv", argv[2]) < 0 ||
        snprintf(faces, sizeof(faces), "%s.face-material.tsv", argv[2]) < 0 ||
        snprintf(groups, sizeof(groups), "%s.face-groups.tsv", argv[2]) < 0) return 4;
    scene = ufbx_load_file(argv[1], &opts, &error);
    if (!scene) {
        fprintf(stderr, "load failed: %.*s\n", (int)error.description.length, error.description.data);
        return 5;
    }
    mesh = find_mesh(scene);
    if (!mesh) { ufbx_free_scene(scene); return 6; }
    if (!(mesh->face_material.count == 0 || mesh->face_material.count == mesh->faces.count)) {
        fputs("partial face material stream rejected\n", stderr); ufbx_free_scene(scene); return 7;
    }
    if (!write_nodes(nodes, mesh) || !write_materials(materials, mesh) || !write_faces(faces, mesh) || !write_groups(groups, mesh)) {
        fputs("output write failed\n", stderr); ufbx_free_scene(scene); return 8;
    }
    printf("{\"ufbx\":\"0.23.0\",\"mesh_element_id\":%" PRIu32 ",\"vertices\":%zu,\"faces\":%zu,\"instances\":%zu,\"materials\":%zu,\"material_parts\":%zu,\"face_material_count\":%zu,\"face_groups\":%zu}\n",
        mesh->element_id, mesh->num_vertices, mesh->num_faces, mesh->instances.count,
        mesh->materials.count, mesh->material_parts.count, mesh->face_material.count,
        mesh->face_groups.count);
    ufbx_free_scene(scene);
    return 0;
}
